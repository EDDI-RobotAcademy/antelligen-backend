"""_to_yahoo_symbol — KR 6자리 종목코드를 KOSPI/KOSDAQ suffix 로 변환."""
import pytest

from app.domains.stock.market_data.adapter.outbound.external import (
    yahoo_finance_daily_bar_fetcher as mod,
)
from app.domains.stock.market_data.adapter.outbound.external.yahoo_finance_daily_bar_fetcher import (
    _to_yahoo_symbol,
)


@pytest.fixture(autouse=True)
def _seed_kr_markets(monkeypatch):
    """pykrx 호출을 우회하기 위해 모듈 캐시를 직접 시드."""
    monkeypatch.setattr(
        mod,
        "_KR_MARKET_CACHE",
        {
            "KOSPI": {"005930", "000660", "035420"},
            "KOSDAQ": {"247540", "091990"},
        },
    )


def test_kospi_ticker_gets_ks_suffix():
    assert _to_yahoo_symbol("005930") == "005930.KS"
    assert _to_yahoo_symbol("000660") == "000660.KS"


def test_kosdaq_ticker_gets_kq_suffix():
    assert _to_yahoo_symbol("247540") == "247540.KQ"
    assert _to_yahoo_symbol("091990") == "091990.KQ"


def test_unknown_kr_ticker_falls_back_to_ks():
    # KOSPI/KOSDAQ 어느 쪽에도 없는 6자리 — .KS fallback (대부분 KOSPI 추정)
    assert _to_yahoo_symbol("999999") == "999999.KS"


def test_us_ticker_unchanged():
    assert _to_yahoo_symbol("AAPL") == "AAPL"
    assert _to_yahoo_symbol("MSFT") == "MSFT"
    assert _to_yahoo_symbol("BRK") == "BRK"


def test_index_ticker_unchanged():
    assert _to_yahoo_symbol("^GSPC") == "^GSPC"
    assert _to_yahoo_symbol("^KS11") == "^KS11"


def test_already_suffixed_ticker_unchanged():
    assert _to_yahoo_symbol("005930.KS") == "005930.KS"
    assert _to_yahoo_symbol("247540.KQ") == "247540.KQ"


def test_empty_string_unchanged():
    assert _to_yahoo_symbol("") == ""


def test_pykrx_failure_falls_back_to_ks(monkeypatch):
    """pykrx 가 실패해도 기능 자체는 죽지 않고 .KS fallback 동작."""
    monkeypatch.setattr(mod, "_KR_MARKET_CACHE", {})

    def _raise(*args, **kwargs):
        raise RuntimeError("pykrx network failure")

    import sys
    import types

    fake_pykrx = types.ModuleType("pykrx")
    fake_stock = types.ModuleType("pykrx.stock")
    fake_stock.get_market_ticker_list = _raise
    fake_pykrx.stock = fake_stock
    monkeypatch.setitem(sys.modules, "pykrx", fake_pykrx)
    monkeypatch.setitem(sys.modules, "pykrx.stock", fake_stock)

    assert _to_yahoo_symbol("005930") == "005930.KS"
