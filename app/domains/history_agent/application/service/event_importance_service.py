"""CORPORATE/ANNOUNCEMENT 이벤트의 종목 단기 영향도를 LLM으로 점수화한다.

- 입력: CORPORATE / ANNOUNCEMENT 카테고리 TimelineEvent 리스트 + 종목 ticker
- 출력: 각 이벤트의 `importance_score` (0.0~1.0) 주석 주입
- 캐시: event_enrichments 테이블에 (ticker, date, type, detail_hash) 키로 점수 영속화

MacroImportanceRanker와의 차이:
- 평가 관점: 시장사 관점이 아니라 **해당 종목의 단기 영향도** 관점
- ticker-scoped: 동일한 type/detail이라도 종목마다 영향도가 다를 수 있어 ticker로 분리 저장
- type별 base score 시드 + LLM 보정: 분포가 거의 고정인 type은 base만으로 결정, 그 외는 LLM이 ±0.15 보정
- 고정 type은 LLM 호출 자체를 skip하여 비용 절감
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

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

EVENT_IMPORTANCE_SYSTEM = """\
당신은 주식 분석가입니다.
각 이벤트가 '해당 종목의 단기 주가에 미치는 영향도'를 0.0~1.0 범위로 점수화하십시오.

점수 기준:
- 1.0: 회사 존립 / 상장 폐지 위험 / 메가딜 (대규모 M&A, 회계 부정 적발, 파산 신청)
- 0.7~0.9: 주요 인수합병, 회계 이슈 발생, 신용등급 강등급 규제 제재
- 0.5~0.7: CEO·CFO 교체, 의미 있는 신제품/계약 발표, 중대한 소송
- 0.3~0.4: 일반 공시, 자사주 매입/소각, 분할/증자
- 0.0~0.2: 정형화된 일상 공시 (연차보고서 제출 등)

판단 시:
- type은 사건 유형의 강한 신호다. 그 위에 detail 본문에서 '규모/금액/심각도'를 보정한다.
- 같은 MERGER_ACQUISITION이라도 100억원 자회사 흡수합병과 50조원 빅딜은 다르다.
- detail에 '소액/단순/일상' 단서가 있으면 base보다 낮게, '대규모/긴급/주요' 단서가 있으면 높게.

규칙:
- JSON 배열로만 응답: [0.73, 0.12, 0.95, ...]
- 이벤트 순서와 배열 순서를 반드시 일치시킨다
- 각 값은 0.0~1.0 사이의 소수 (최대 2자리)
- 추가 설명 금지
"""

# type별 base score 시드. 분포가 거의 고정인 type은 LLM skip 가능.
# `_LLM_SKIP_TYPES`에 있으면 base만으로 결정, 그 외 type은 LLM이 detail 기반 보정.
_TYPE_BASE_SCORE: Dict[str, float] = {
    # ANNOUNCEMENT
    "CRISIS": 0.85,
    "ACCOUNTING_ISSUE": 0.75,
    "MERGER_ACQUISITION": 0.70,
    "REGULATORY": 0.60,
    "MANAGEMENT_CHANGE": 0.50,
    "PRODUCT_LAUNCH": 0.45,
    "MAJOR_EVENT": 0.40,
    "CONTRACT": 0.35,
    # CORPORATE
    "RIGHTS_OFFERING": 0.55,
    "BUYBACK_CANCEL": 0.50,
    "BUYBACK": 0.45,
    "STOCK_SPLIT": 0.35,
    "DISCLOSURE": 0.30,
}

# 분포가 좁아 LLM 호출 가치가 낮은 type. base만으로 점수 결정.
_LLM_SKIP_TYPES = {"DISCLOSURE", "STOCK_SPLIT", "MAJOR_EVENT"}

_FALLBACK_SCORE = 0.3
_BATCH_SIZE = 20
_CONCURRENCY = 4
_JSON_RETRY_SUFFIX = (
    "\n\n반드시 0.0~1.0 사이 숫자로 구성된 JSON 배열만 출력하세요. 설명·코드펜스 금지."
)


def _base_score(event_type: str) -> float:
    return _TYPE_BASE_SCORE.get(event_type, _FALLBACK_SCORE)


def _build_line(idx: int, event: TimelineEvent) -> str:
    base = _base_score(event.type)
    return (
        f"{idx + 1}. type={event.type} base={base:.2f} "
        f"date={event.date.isoformat()} detail={event.detail[:200]}"
    )


async def _invoke_llm(llm: Any, system_prompt: str, lines: str) -> str:
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=lines),
    ])
    return response.content.strip()


def _parse_scores(content: str, expected: int) -> List[float]:
    parsed = json.loads(content)
    if not isinstance(parsed, list):
        raise json.JSONDecodeError("expected list", content, 0)
    if len(parsed) != expected:
        raise json.JSONDecodeError(
            f"expected {expected} items, got {len(parsed)}", content, 0,
        )
    return [max(0.0, min(1.0, float(v))) for v in parsed]


async def _score_batch(
    llm: Any, batch: List[TimelineEvent], sem: asyncio.Semaphore
) -> List[float]:
    lines = "\n".join(_build_line(i, e) for i, e in enumerate(batch))
    async with sem:
        try:
            content = await _invoke_llm(llm, EVENT_IMPORTANCE_SYSTEM, lines)
            return _parse_scores(content, len(batch))
        except json.JSONDecodeError as exc:
            logger.warning("[EventImportance] JSON 파싱 실패, 재시도: %s", exc)
            try:
                content = await _invoke_llm(
                    llm, EVENT_IMPORTANCE_SYSTEM + _JSON_RETRY_SUFFIX, lines,
                )
                return _parse_scores(content, len(batch))
            except Exception as retry_exc:
                logger.warning(
                    "[EventImportance] 재시도 실패 → type base score 할당: %s", retry_exc,
                )
                return [_base_score(e.type) for e in batch]
        except Exception as exc:
            logger.warning(
                "[EventImportance] 점수화 실패 → type base score 할당: %s", exc,
            )
            return [_base_score(e.type) for e in batch]


def _build_cache_key(
    ticker: str, event: TimelineEvent
) -> Tuple[str, Any, str, str]:
    return (
        ticker,
        event.date,
        event.type,
        compute_detail_hash(event.detail),
    )


_SCOREABLE_CATEGORIES = {"CORPORATE", "ANNOUNCEMENT"}


class EventImportanceService:
    """LLM 기반 종목 이벤트 영향도 채점기 + DB 점수 캐시."""

    def __init__(self, enrichment_repo: EventEnrichmentRepositoryPort):
        self._repo = enrichment_repo

    async def score(self, ticker: str, events: List[TimelineEvent]) -> None:
        """events 중 CORPORATE/ANNOUNCEMENT에 importance_score를 in-place로 채운다.

        - 이미 importance_score가 설정된 이벤트는 건드리지 않는다
        - DB 캐시 적중 분은 LLM 호출 없이 재사용
        - _LLM_SKIP_TYPES에 속한 type은 base score만 즉시 할당 (LLM skip)
        - 실패 시 type별 base score로 fallback
        """
        if not events:
            return

        targets = [
            e for e in events
            if e.category in _SCOREABLE_CATEGORIES and e.importance_score is None
        ]
        if not targets:
            return

        start = time.monotonic()
        keys = [_build_cache_key(ticker, e) for e in targets]
        logger.info(
            "[EventImportance] 시작: ticker=%s targets=%d", ticker, len(targets),
        )

        try:
            cached = await self._repo.find_by_keys(keys)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[EventImportance] find_by_keys 실패 — 상위에서 세션 롤백 필요: %s", exc,
            )
            raise
        cache_map: Dict[Tuple, EventEnrichment] = {
            (r.ticker, r.event_date, r.event_type, r.detail_hash): r for r in cached
        }

        # 1) 캐시 적중 / LLM skip type 즉시 처리
        miss_events: List[TimelineEvent] = []
        miss_indices: List[int] = []
        miss_keys: List[Tuple[str, Any, str, str]] = []
        new_rows: List[EventEnrichment] = []
        cache_hit = 0
        skip_count = 0

        for idx, event in enumerate(targets):
            key = keys[idx]
            hit = cache_map.get(key)
            if hit and hit.importance_score is not None:
                event.importance_score = hit.importance_score
                cache_hit += 1
                continue

            if event.type in _LLM_SKIP_TYPES:
                score = _base_score(event.type)
                event.importance_score = score
                skip_count += 1
                ticker_k, event_date, event_type, detail_hash = key
                new_rows.append(
                    EventEnrichment(
                        ticker=ticker_k,
                        event_date=event_date,
                        event_type=event_type,
                        detail_hash=detail_hash,
                        title=event.title or event.type,
                        importance_score=score,
                    )
                )
                continue

            miss_events.append(event)
            miss_indices.append(idx)
            miss_keys.append(key)

        # 2) 남은 miss는 LLM 채점
        if miss_events:
            llm = get_workflow_llm(model=TITLE_MODEL)
            sem = asyncio.Semaphore(_CONCURRENCY)
            tasks = [
                _score_batch(llm, miss_events[i: i + _BATCH_SIZE], sem)
                for i in range(0, len(miss_events), _BATCH_SIZE)
            ]
            batch_results = await asyncio.gather(*tasks)
            flat_scores: List[float] = []
            for batch in batch_results:
                flat_scores.extend(batch)

            for idx_in_miss, score in enumerate(flat_scores):
                event = miss_events[idx_in_miss]
                event.importance_score = score
                ticker_k, event_date, event_type, detail_hash = miss_keys[idx_in_miss]
                new_rows.append(
                    EventEnrichment(
                        ticker=ticker_k,
                        event_date=event_date,
                        event_type=event_type,
                        detail_hash=detail_hash,
                        title=event.title or event.type,
                        importance_score=score,
                    )
                )
            llm_calls = len(miss_events)
        else:
            llm_calls = 0

        # 3) 새로 계산된 점수만 DB 영속화
        if new_rows:
            try:
                await self._repo.upsert_bulk(new_rows)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[EventImportance] 점수 저장 실패 (무시): %s", exc)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "[EventImportance] 완료: ticker=%s cache_hit=%d skip=%d llm=%d total=%d elapsed=%dms",
            ticker, cache_hit, skip_count, llm_calls, len(targets), elapsed_ms,
            extra={
                "llm_op": "event_importance",
                "ticker": ticker,
                "cache_hit": cache_hit,
                "skip_count": skip_count,
                "llm_calls": llm_calls,
                "total": len(targets),
                "elapsed_ms": elapsed_ms,
            },
        )
