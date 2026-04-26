"""ANNOUNCEMENT 이벤트의 type을 LLM으로 재분류한다 (v2 분류기, KR A.1).

목적:
- 규칙 베이스 분류(_ITEM_TYPE_MAP, _TITLE_KEYWORD_MAP)에서 MAJOR_EVENT(fallback)으로 떨어진
  이벤트만 LLM으로 더 정확한 type에 재할당.
- AAPL 같은 대기업의 정기 IR 공시(분기 실적, 회사채 발행, 주총 등)가 MAJOR_EVENT로 묶이는 문제 해소.
- 비용 최소화: MAJOR_EVENT만 대상이라 ticker당 LLM 호출 5~10건 수준 추가.

설계:
- 입력: items_str + title + detail. 8-K Item 코드는 강한 신호이므로 가능하면 보존.
- 출력: 12개 후보 type 중 하나(JSON 배열).
- DB 캐시: classifier_version='v2'로 새 행 추가. v1 행은 보존.
  - UK가 (ticker, date, event_type=원본, detail_hash, classifier_version)이라 새 type을 별도
    `reclassified_type` 컬럼에 저장. find_by_keys는 원본 event_type으로 검색 가능.
- LLM 실패 시: 현 type(MAJOR_EVENT) 유지 — 잘못된 재분류보다 안전.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from app.domains.dashboard.domain.entity.announcement_event import AnnouncementEventType
from app.domains.history_agent.application.port.out.event_enrichment_repository_port import (
    EventEnrichmentRepositoryPort,
)
from app.domains.history_agent.application.response.timeline_response import TimelineEvent
from app.domains.history_agent.application.service.title_generation_service import (
    TITLE_MODEL,
)
from app.domains.history_agent.domain.entity.event_enrichment import (
    EventEnrichment,
    compute_detail_hash,
)
from app.infrastructure.langgraph.llm_factory import get_workflow_llm

logger = logging.getLogger(__name__)

# 12개 후보 type. 기존 8 + 신규 4(EARNINGS_RELEASE/DEBT_ISSUANCE/SHAREHOLDER_MEETING/REGULATION_FD).
_CANDIDATE_TYPES: List[str] = [t.value for t in AnnouncementEventType]

# v2 분류기는 ANNOUNCEMENT + MAJOR_EVENT만 재분류한다(=fallback에서 더 적절한 type 찾기).
# 명시 type(MERGER_ACQUISITION 등)으로 이미 분류된 건은 신뢰하고 건드리지 않음.
_RECLASSIFY_TYPES = {AnnouncementEventType.MAJOR_EVENT.value}

EVENT_CLASSIFIER_V2_SYSTEM = """\
당신은 SEC 8-K 공시 분석가입니다.
각 공시의 Item 코드와 본문을 보고, 다음 12개 type 중 가장 적합한 하나를 선택하십시오.

후보 type:
- MERGER_ACQUISITION: 합병/인수/지배구조 변경 (Item 2.01)
- CONTRACT: 중요 계약/MOU/파트너십 체결·종료 (Item 1.01/1.02)
- MANAGEMENT_CHANGE: CEO/임원 교체·사임 (Item 5.02)
- ACCOUNTING_ISSUE: 회계 부정/재무제표 정정 (Item 4.02)
- REGULATORY: 규제·소송·제재·과징금
- PRODUCT_LAUNCH: 신제품/신기술 출시·발표
- CRISIS: 상장폐지·파산·리콜·거래정지 (Item 3.01)
- EARNINGS_RELEASE: 분기/연간 실적 발표 (Item 2.02 — 정기 IR)
- DEBT_ISSUANCE: 회사채/사채/notes 발행, 자본 조달
- SHAREHOLDER_MEETING: 정기/임시 주주총회 결과 (Item 5.07)
- REGULATION_FD: Reg FD 공정공시 (Item 7.01) — 가이던스 변경 등
- ARTICLES_AMENDMENT: 정관/부속법 개정 (Item 5.03) — 지배구조·주주권·M&A 방어 조항 변경
- MAJOR_EVENT: 위 어디에도 명확히 속하지 않는 기타 중요사항

판단 가이드:
- Item 코드는 강한 신호. 2.02→EARNINGS_RELEASE, 5.07→SHAREHOLDER_MEETING, 7.01→REGULATION_FD, 5.03→ARTICLES_AMENDMENT 우선.
- 8.01(Other Events)이면 본문 내용으로 판단. 회사채 발행이면 DEBT_ISSUANCE, 그 외 정기 IR이면 REGULATION_FD.
- 본문에 "quarterly results", "earnings", "Q4 results" → EARNINGS_RELEASE.
- 본문에 "notes due", "senior notes", "bond" → DEBT_ISSUANCE.
- 본문에 "annual meeting", "voted" → SHAREHOLDER_MEETING.
- 어느 것에도 명확하지 않으면 MAJOR_EVENT 유지.

규칙:
- JSON 배열로만 응답: ["EARNINGS_RELEASE", "DEBT_ISSUANCE", "MAJOR_EVENT", ...]
- 이벤트 순서와 배열 순서를 반드시 일치시킨다
- 후보 12개 중 하나만 선택. 다른 문자열 출력 금지.
- 추가 설명 금지.
"""

_BATCH_SIZE = 20
_CONCURRENCY = 4
_JSON_RETRY_SUFFIX = (
    "\n\n반드시 12개 후보 중 하나로 구성된 JSON 배열만 출력하세요. 설명·코드펜스 금지."
)


def _build_line(idx: int, event: TimelineEvent) -> str:
    items = event.items_str or "?"
    detail = (event.detail or "")[:300]
    title = (event.title or "")[:80]
    return f"{idx + 1}. items=[{items}] title={title!r} detail={detail!r}"


async def _invoke_llm(llm: Any, system_prompt: str, lines: str) -> str:
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=lines),
    ])
    return response.content.strip()


def _parse_types(content: str, expected: int) -> List[str]:
    parsed = json.loads(content)
    if not isinstance(parsed, list):
        raise json.JSONDecodeError("expected list", content, 0)
    if len(parsed) != expected:
        raise json.JSONDecodeError(
            f"expected {expected} items, got {len(parsed)}", content, 0,
        )
    result = []
    for v in parsed:
        if not isinstance(v, str) or v not in _CANDIDATE_TYPES:
            # 후보 외 값은 MAJOR_EVENT로 안전 fallback.
            result.append(AnnouncementEventType.MAJOR_EVENT.value)
        else:
            result.append(v)
    return result


async def _classify_batch(
    llm: Any, batch: List[TimelineEvent], sem: asyncio.Semaphore
) -> List[str]:
    lines = "\n".join(_build_line(i, e) for i, e in enumerate(batch))
    async with sem:
        try:
            content = await _invoke_llm(llm, EVENT_CLASSIFIER_V2_SYSTEM, lines)
            return _parse_types(content, len(batch))
        except json.JSONDecodeError as exc:
            logger.warning("[EventClassifier] JSON 파싱 실패, 재시도: %s", exc)
            try:
                content = await _invoke_llm(
                    llm, EVENT_CLASSIFIER_V2_SYSTEM + _JSON_RETRY_SUFFIX, lines,
                )
                return _parse_types(content, len(batch))
            except Exception as retry_exc:
                logger.warning(
                    "[EventClassifier] 재시도 실패 → MAJOR_EVENT 유지: %s", retry_exc,
                )
                return [AnnouncementEventType.MAJOR_EVENT.value] * len(batch)
        except Exception as exc:
            logger.warning(
                "[EventClassifier] 분류 실패 → MAJOR_EVENT 유지: %s", exc,
            )
            return [AnnouncementEventType.MAJOR_EVENT.value] * len(batch)


def _build_v2_cache_key(
    ticker: str, event: TimelineEvent
) -> Tuple[str, Any, str, str, str]:
    """v2 분류기 캐시 키. event_type은 항상 원본(MAJOR_EVENT 등) 유지하여
    재분류 결과(reclassified_type)는 별도 컬럼에 저장한다.
    """
    return (
        ticker,
        event.date,
        event.type,
        compute_detail_hash(event.detail),
        "v2",
    )


class EventClassifierService:
    """LLM 기반 ANNOUNCEMENT type 재분류기 + DB 캐시 (classifier_version='v2')."""

    def __init__(self, enrichment_repo: EventEnrichmentRepositoryPort):
        self._repo = enrichment_repo

    async def classify(self, ticker: str, events: List[TimelineEvent]) -> None:
        """events 중 ANNOUNCEMENT + MAJOR_EVENT 이벤트의 type을 in-place로 재할당.

        - DB 캐시 적중분은 LLM 호출 없이 재사용 (reclassified_type 컬럼 활용)
        - LLM 결과가 MAJOR_EVENT면 변경 없음 (event.type 유지)
        - 재분류 성공 시 event.type 갱신 + classifier_version='v2' 마크 + DB 영속화
        """
        if not events:
            return

        targets = [
            e for e in events
            if e.category == "ANNOUNCEMENT" and e.type in _RECLASSIFY_TYPES
        ]
        if not targets:
            return

        start = time.monotonic()
        keys = [_build_v2_cache_key(ticker, e) for e in targets]
        logger.info(
            "[EventClassifier] 시작: ticker=%s targets=%d", ticker, len(targets),
        )

        try:
            cached = await self._repo.find_by_keys(keys)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[EventClassifier] find_by_keys 실패 — 상위에서 세션 롤백 필요: %s", exc,
            )
            raise
        cache_map: Dict[Tuple, EventEnrichment] = {
            (r.ticker, r.event_date, r.event_type, r.detail_hash, r.classifier_version): r
            for r in cached
        }

        # 1) 캐시 적중 처리 — reclassified_type을 event.type에 적용
        miss_events: List[TimelineEvent] = []
        miss_keys: List[Tuple[str, Any, str, str, str]] = []
        cache_hit = 0
        reclassified = 0

        for idx, event in enumerate(targets):
            key = keys[idx]
            hit = cache_map.get(key)
            if hit and hit.reclassified_type:
                if hit.reclassified_type != event.type:
                    event.type = hit.reclassified_type
                    event.classifier_version = "v2"
                    reclassified += 1
                cache_hit += 1
                continue

            miss_events.append(event)
            miss_keys.append(key)

        # 2) LLM 호출
        new_rows: List[EventEnrichment] = []
        if miss_events:
            llm = get_workflow_llm(model=TITLE_MODEL)
            sem = asyncio.Semaphore(_CONCURRENCY)
            tasks = [
                _classify_batch(llm, miss_events[i: i + _BATCH_SIZE], sem)
                for i in range(0, len(miss_events), _BATCH_SIZE)
            ]
            batch_results = await asyncio.gather(*tasks)
            flat_types: List[str] = []
            for batch in batch_results:
                flat_types.extend(batch)

            for idx_in_miss, new_type in enumerate(flat_types):
                event = miss_events[idx_in_miss]
                ticker_k, event_date, original_type, detail_hash, _version = miss_keys[idx_in_miss]

                if new_type != event.type:
                    event.type = new_type
                    event.classifier_version = "v2"
                    reclassified += 1

                # v2 행은 항상 새로 저장 (LLM 호출 비용 회수). reclassified_type=NEW_TYPE.
                # event_type은 원본(MAJOR_EVENT) 유지해 캐시 키 일관성 보존.
                new_rows.append(
                    EventEnrichment(
                        ticker=ticker_k,
                        event_date=event_date,
                        event_type=original_type,
                        detail_hash=detail_hash,
                        title=(event.title or original_type)[:500],
                        reclassified_type=new_type,
                        classifier_version="v2",
                    )
                )

            llm_calls = len(miss_events)
        else:
            llm_calls = 0

        # 3) DB 영속화
        if new_rows:
            try:
                await self._repo.upsert_bulk(new_rows)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[EventClassifier] 영속화 실패 (무시): %s", exc)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "[EventClassifier] 완료: ticker=%s cache_hit=%d llm=%d reclassified=%d total=%d elapsed=%dms",
            ticker, cache_hit, llm_calls, reclassified, len(targets), elapsed_ms,
            extra={
                "llm_op": "event_classifier_v2",
                "ticker": ticker,
                "cache_hit": cache_hit,
                "llm_calls": llm_calls,
                "reclassified": reclassified,
                "total": len(targets),
                "elapsed_ms": elapsed_ms,
            },
        )
