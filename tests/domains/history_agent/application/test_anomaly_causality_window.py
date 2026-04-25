"""§13.4 D — chart_interval 별 causality lookback 윈도우 + 캐시 키 분리."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.history_agent.application.usecase.get_anomaly_causality_usecase import (
    GetAnomalyCausalityUseCase,
    _CHART_INTERVAL_WINDOW_MULTIPLIER,
)


def _mk_repo(cache_hit=False):
    repo = MagicMock()
    if cache_hit:
        cached = MagicMock()
        cached.causality = []
        repo.find_by_keys = AsyncMock(return_value=[cached])
    else:
        repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=1)
    repo.rollback = AsyncMock()
    return repo


def test_window_multiplier_table_aligns_to_chart_interval():
    """봉 단위가 길수록 lookback 윈도우 배수도 큼 — 일봉 단일 사건 vs 분기봉 거시 trend."""
    assert _CHART_INTERVAL_WINDOW_MULTIPLIER == {
        "1D": 1,
        "1W": 7,
        "1M": 30,
        "1Q": 90,
        "1Y": 90,
    }


@pytest.mark.asyncio
async def test_cache_key_differs_per_chart_interval(monkeypatch):
    """동일 (ticker, bar_date) 라도 chart_interval 다르면 캐시 키 다름."""
    repo = _mk_repo(cache_hit=False)
    usecase = GetAnomalyCausalityUseCase(enrichment_repo=repo)

    # run_causality_agent 외부 의존성 mock
    async def _fake_agent(**kwargs):
        return {"hypotheses": []}

    import app.domains.causality_agent.application.causality_agent_workflow as workflow_module
    monkeypatch.setattr(workflow_module, "run_causality_agent", _fake_agent)

    await usecase.execute(ticker="AAPL", bar_date=date(2026, 4, 1), chart_interval="1D")
    await usecase.execute(ticker="AAPL", bar_date=date(2026, 4, 1), chart_interval="1Q")

    # find_by_keys 가 두 번 호출되고 각 키의 detail_hash 가 다름
    assert repo.find_by_keys.await_count == 2
    key_1d = repo.find_by_keys.await_args_list[0].args[0][0]  # (ticker, date, type, hash)
    key_1q = repo.find_by_keys.await_args_list[1].args[0][0]
    assert key_1d[3] != key_1q[3]


@pytest.mark.asyncio
async def test_lookback_days_multiplied_by_chart_interval(monkeypatch):
    """1Q chart_interval 시 pre/post days 가 settings × 90 으로 확장."""
    repo = _mk_repo(cache_hit=False)
    usecase = GetAnomalyCausalityUseCase(enrichment_repo=repo)

    captured = {}
    async def _fake_agent(**kwargs):
        captured["start"] = kwargs["start_date"]
        captured["end"] = kwargs["end_date"]
        return {"hypotheses": []}

    import app.domains.causality_agent.application.causality_agent_workflow as workflow_module
    monkeypatch.setattr(workflow_module, "run_causality_agent", _fake_agent)

    bar_date = date(2026, 4, 1)
    await usecase.execute(ticker="AAPL", bar_date=bar_date, chart_interval="1Q")

    # default settings: history_causality_pre_days=14, post_days=3
    # × 90 = pre 1260, post 270
    assert (bar_date - captured["start"]).days == 14 * 90
    assert (captured["end"] - bar_date).days == 3 * 90


@pytest.mark.asyncio
async def test_no_chart_interval_uses_default_multiplier(monkeypatch):
    """chart_interval=None 이면 multiplier=1 (기존 동작 유지)."""
    repo = _mk_repo(cache_hit=False)
    usecase = GetAnomalyCausalityUseCase(enrichment_repo=repo)

    captured = {}
    async def _fake_agent(**kwargs):
        captured["start"] = kwargs["start_date"]
        captured["end"] = kwargs["end_date"]
        return {"hypotheses": []}

    import app.domains.causality_agent.application.causality_agent_workflow as workflow_module
    monkeypatch.setattr(workflow_module, "run_causality_agent", _fake_agent)

    bar_date = date(2026, 4, 1)
    await usecase.execute(ticker="AAPL", bar_date=bar_date)

    # 기본값 14/3 (multiplier=1)
    assert (bar_date - captured["start"]).days == 14
    assert (captured["end"] - bar_date).days == 3
