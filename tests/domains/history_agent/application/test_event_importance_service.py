"""EventImportanceService — type별 base score + LLM 보정 + DB 캐시 + skip 최적화."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.history_agent.application.response.timeline_response import TimelineEvent
from app.domains.history_agent.application.service.event_importance_service import (
    EventImportanceService,
    _LLM_SKIP_TYPES,
    _TYPE_BASE_SCORE,
    _FALLBACK_SCORE,
)
from app.domains.history_agent.domain.entity.event_enrichment import (
    EventEnrichment,
    compute_detail_hash,
)

pytestmark = pytest.mark.asyncio


def _event(
    idx: int,
    *,
    category: str = "ANNOUNCEMENT",
    event_type: str = "MERGER_ACQUISITION",
    detail: str | None = None,
) -> TimelineEvent:
    return TimelineEvent(
        title=f"title-{idx}",
        date=datetime.date(2024, 1, idx + 1),
        category=category,
        type=event_type,
        detail=detail or f"detail-{idx}",
    )


class _FakeLLM:
    def __init__(self, scores: list[float]):
        self._payload = f"{scores}"
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        mock_response = MagicMock()
        mock_response.content = self._payload
        return mock_response


async def test_service_assigns_llm_scores_and_persists():
    events = [
        _event(0, event_type="MERGER_ACQUISITION"),
        _event(1, event_type="REGULATORY"),
        _event(2, event_type="CRISIS"),
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=3)

    fake_llm = _FakeLLM([0.78, 0.55, 0.92])

    with patch(
        "app.domains.history_agent.application.service.event_importance_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventImportanceService(enrichment_repo=repo)
        await service.score("AAPL", events)

    assert [round(e.importance_score or 0, 2) for e in events] == [0.78, 0.55, 0.92]
    assert fake_llm.calls == 1
    repo.upsert_bulk.assert_awaited_once()
    saved = repo.upsert_bulk.call_args.args[0]
    assert len(saved) == 3
    assert all(isinstance(row, EventEnrichment) for row in saved)
    assert all(row.ticker == "AAPL" for row in saved)
    assert all(row.importance_score is not None for row in saved)


async def test_service_skips_llm_for_disclosure_and_stock_split():
    """DISCLOSURE / STOCK_SPLIT은 분포가 좁아 LLM 호출 없이 base score만 할당."""
    events = [
        _event(0, category="CORPORATE", event_type="DISCLOSURE"),
        _event(1, category="CORPORATE", event_type="STOCK_SPLIT"),
        _event(2, event_type="MERGER_ACQUISITION"),
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=3)

    fake_llm = _FakeLLM([0.75])  # MERGER_ACQUISITION만 LLM 호출

    with patch(
        "app.domains.history_agent.application.service.event_importance_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventImportanceService(enrichment_repo=repo)
        await service.score("AAPL", events)

    assert events[0].importance_score == _TYPE_BASE_SCORE["DISCLOSURE"]
    assert events[1].importance_score == _TYPE_BASE_SCORE["STOCK_SPLIT"]
    assert events[2].importance_score == 0.75
    assert fake_llm.calls == 1  # MERGER_ACQUISITION 1건만 LLM 호출


async def test_service_uses_cache_when_available():
    events = [_event(0, event_type="REGULATORY"), _event(1, event_type="CONTRACT")]
    cached = [
        EventEnrichment(
            ticker="AAPL",
            event_date=events[0].date,
            event_type=events[0].type,
            detail_hash=compute_detail_hash(events[0].detail),
            title=events[0].title,
            importance_score=0.66,
        )
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=cached)
    repo.upsert_bulk = AsyncMock(return_value=1)

    fake_llm = _FakeLLM([0.4])

    with patch(
        "app.domains.history_agent.application.service.event_importance_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventImportanceService(enrichment_repo=repo)
        await service.score("AAPL", events)

    assert events[0].importance_score == 0.66  # from cache
    assert round(events[1].importance_score or 0, 2) == 0.4  # from LLM
    assert fake_llm.calls == 1


async def test_service_skips_macro_and_preassigned_events():
    """MACRO 이벤트(다른 service 담당)와 이미 점수 있는 이벤트는 건드리지 않는다."""
    events = [
        _event(0, category="MACRO", event_type="CRISIS"),  # MACRO → skip
        _event(1, event_type="MERGER_ACQUISITION"),
    ]
    events[1].importance_score = 0.95  # 이미 채워짐 → skip

    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=0)

    fake_llm = _FakeLLM([0.0])

    with patch(
        "app.domains.history_agent.application.service.event_importance_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventImportanceService(enrichment_repo=repo)
        await service.score("AAPL", events)

    assert events[0].importance_score is None  # MACRO 건드리지 않음
    assert events[1].importance_score == 0.95  # preassigned 유지
    assert fake_llm.calls == 0
    repo.find_by_keys.assert_not_awaited()  # targets가 비어있어 호출조차 안 함


async def test_service_falls_back_to_type_base_on_llm_failure():
    events = [
        _event(0, event_type="MERGER_ACQUISITION"),
        _event(1, event_type="CONTRACT"),
        _event(2, event_type="UNKNOWN_TYPE"),
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=3)

    broken_llm = MagicMock()
    broken_llm.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

    with patch(
        "app.domains.history_agent.application.service.event_importance_service.get_workflow_llm",
        return_value=broken_llm,
    ):
        service = EventImportanceService(enrichment_repo=repo)
        await service.score("AAPL", events)

    # type별 base score로 fallback (단일 fallback 0.3이 아님)
    assert events[0].importance_score == _TYPE_BASE_SCORE["MERGER_ACQUISITION"]
    assert events[1].importance_score == _TYPE_BASE_SCORE["CONTRACT"]
    assert events[2].importance_score == _FALLBACK_SCORE  # 미지원 type → 0.3


async def test_service_handles_empty_input():
    repo = MagicMock()
    service = EventImportanceService(enrichment_repo=repo)
    await service.score("AAPL", [])
    repo.find_by_keys.assert_not_called() if hasattr(repo.find_by_keys, "assert_not_called") else None


async def test_skip_types_are_subset_of_base_scores():
    """LLM skip type은 반드시 base score 테이블에 있어야 한다."""
    for skip_type in _LLM_SKIP_TYPES:
        assert skip_type in _TYPE_BASE_SCORE, f"{skip_type} missing from _TYPE_BASE_SCORE"
