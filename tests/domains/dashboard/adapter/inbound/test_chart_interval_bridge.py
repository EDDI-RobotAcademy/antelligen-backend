"""§13.8 Phase 3: dashboard_router._validate_chart_interval 단위 테스트.

- chart_interval 만 허용 (period deprecation 완료)
- 유효값(1D/1W/1M/1Y) → 그대로 반환
- 유효하지 않은 값 → 400
"""

import pytest

from app.common.exception.app_exception import AppException
from app.domains.dashboard.adapter.inbound.api.dashboard_router import _validate_chart_interval


class TestValidateChartInterval:
    @pytest.mark.parametrize("value", ["1D", "1W", "1M", "1Y"])
    def test_all_valid_values_pass_through(self, value):
        assert _validate_chart_interval(value) == value

    def test_invalid_value_raises_400(self):
        with pytest.raises(AppException) as exc:
            _validate_chart_interval("5Y")
        assert exc.value.status_code == 400
        assert "유효하지 않은 chart_interval" in exc.value.message

    def test_legacy_1q_value_raises_400_at_dashboard(self):
        # dashboard 의 _VALID_PERIODS 는 1D/1W/1M/1Y. 1Q 는 history_agent 만 허용.
        with pytest.raises(AppException) as exc:
            _validate_chart_interval("1Q")
        assert exc.value.status_code == 400

    def test_empty_string_raises_400(self):
        with pytest.raises(AppException) as exc:
            _validate_chart_interval("")
        assert exc.value.status_code == 400
