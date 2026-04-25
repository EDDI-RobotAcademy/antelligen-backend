"""ADR-0001 호환 브리지 단위 테스트.

dashboard_router 의 `_resolve_chart_interval` 헬퍼가:
- `chart_interval` 우선
- `period` 는 deprecation alias 로 fallback
- 둘 다 없으면 default
- 유효하지 않은 값은 400
"""

import pytest

from app.common.exception.app_exception import AppException
from app.domains.dashboard.adapter.inbound.api.dashboard_router import _resolve_chart_interval


class TestResolveChartInterval:
    def test_chart_interval_takes_precedence_over_period(self):
        assert _resolve_chart_interval("1Y", "1D", "1M") == "1Y"

    def test_period_used_when_chart_interval_none(self):
        assert _resolve_chart_interval(None, "1W", "1M") == "1W"

    def test_default_used_when_both_none(self):
        assert _resolve_chart_interval(None, None, "1M") == "1M"

    @pytest.mark.parametrize("value", ["1D", "1W", "1M", "1Y"])
    def test_all_valid_values_accepted(self, value):
        assert _resolve_chart_interval(value, None, "1M") == value
        assert _resolve_chart_interval(None, value, "1M") == value

    def test_invalid_chart_interval_raises_400(self):
        with pytest.raises(AppException) as exc:
            _resolve_chart_interval("5Y", None, "1M")
        assert exc.value.status_code == 400
        assert "유효하지 않은 chart_interval" in exc.value.message

    def test_invalid_period_alias_raises_400(self):
        with pytest.raises(AppException) as exc:
            _resolve_chart_interval(None, "1Q", "1M")
        assert exc.value.status_code == 400

    def test_empty_string_chart_interval_falls_back_to_period(self):
        # FastAPI Query 가 빈 문자열을 보내는 엣지 — falsy 평가로 period fallback
        assert _resolve_chart_interval("", "1D", "1M") == "1D"
