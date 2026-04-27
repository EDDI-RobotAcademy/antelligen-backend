"""차트 이상치 봉 감지 UseCase (§13.4 C, §17.2, OKR 다층 탐지).

다층 탐지기:
1. **z-score (기존)** — 봉 단위 adaptive threshold (k·σ + floor) 로 "이 봉이 평상시보다 특이한가"
2. **cumulative window (KR2)** — 1D 에서 5/20일 누적 수익률 ±10/15% 임계 진입 봉

- k: 2.5 공통 (표준편차 배수)
- window: 봉 단위별 σ 추정 기간
- floor: 봉 단위별 절대 하한 변동률(%) — 1D 에선 KR1 종목 군별 floor 가 우선
- max_count: 봉 단위별 최대 마커 수

KR1 종목 군별 floor 우선순위 (1D 에만 적용):
- KOSPI(`.KS`): 5%   / KOSDAQ(`.KQ`): 7%   / 그 외(미국 등): 5%
미국 대/소형(S&P/Russell) 세분화는 시가총액 메타 인프라 필요해 보류.

향후 follow-up: KR3 Drawdown / KR4 MAD 변동성 정규화 / KR5 변동성 클러스터.
"""
import logging
import math
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.domains.dashboard.application.port.out.stock_bars_port import StockBarsPort
from app.domains.dashboard.domain.entity.stock_bar import StockBar
from app.domains.history_agent.application.response.anomaly_bar_response import (
    AnomalyBarResponse,
    AnomalyBarsResponse,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _IntervalParams:
    k: float
    window: int
    floor_pct: float
    max_count: int


# §17.2 표. k 공통 2.5. floor는 봉 단위 증가에 따라 상향 (시간 범위가 길수록 noise floor↑).
_PARAMS_BY_INTERVAL: dict[str, _IntervalParams] = {
    "1D": _IntervalParams(k=2.5, window=60,  floor_pct=2.0,  max_count=20),
    "1W": _IntervalParams(k=2.5, window=52,  floor_pct=3.0,  max_count=15),
    "1M": _IntervalParams(k=2.5, window=36,  floor_pct=5.0,  max_count=10),
    "1Q": _IntervalParams(k=2.5, window=40,  floor_pct=10.0, max_count=5),
}


# KR1 — 종목 군별 1D floor (`max(k×σ, group_floor)`).
# 군 식별은 yfinance ticker suffix 기반(.KS=KOSPI, .KQ=KOSDAQ, 그 외=US).
_FLOOR_BY_TICKER_GROUP_1D: Dict[str, float] = {
    "KOSPI": 5.0,
    "KOSDAQ": 7.0,
    "US": 5.0,
}


def _classify_ticker_group(ticker: str) -> str:
    """yfinance suffix 로 거래소 군 분류. 미정의 종목은 'US' 로 fallback(보수적)."""
    upper = (ticker or "").upper()
    if upper.endswith(".KS"):
        return "KOSPI"
    if upper.endswith(".KQ"):
        return "KOSDAQ"
    return "US"


def _floor_pct_for(chart_interval: str, ticker: str, default: float) -> float:
    """1D 면 종목 군별 floor 우선, 그 외 봉 단위는 default(`_PARAMS_BY_INTERVAL`) 그대로."""
    if chart_interval != "1D":
        return default
    return _FLOOR_BY_TICKER_GROUP_1D.get(_classify_ticker_group(ticker), default)


# KR2 — 누적 윈도우 임계값(1D 전용).
# 임계 이상으로 처음 진입한 봉만 마커 trigger — 빠져나간 후 재진입 시 재 트리거.
_CUMULATIVE_5D_THRESHOLD = 0.10   # ±10%
_CUMULATIVE_20D_THRESHOLD = 0.15  # ±15%


def _compute_returns(bars: List[StockBar]) -> list[float]:
    """봉 단위 일(또는 주/월/분기)수익률. bars 배열과 **1만큼 짧은** 배열 반환.

    idx i 의 return = (bars[i+1].close - bars[i].close) / bars[i].close
    """
    returns: list[float] = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1].close
        if prev_close <= 0:
            returns.append(0.0)
            continue
        returns.append(bars[i].close / prev_close - 1.0)
    return returns


def _volume_ratio(bars: List[StockBar], idx: int, window: int) -> Optional[float]:
    """idx 봉의 거래량을 직전 window 봉 평균 대비 배수로 환산. 평균이 0/window 부족이면 None."""
    if idx < window:
        return None
    window_volumes = [bars[j].volume for j in range(idx - window, idx) if bars[j].volume > 0]
    if not window_volumes:
        return None
    avg = sum(window_volumes) / len(window_volumes)
    if avg <= 0:
        return None
    return round(bars[idx].volume / avg, 4)


def _time_of_day(bars: List[StockBar], idx: int, chart_interval: str) -> Optional[str]:
    """일봉(1D)에서만 갭/장중 근사. |open-prev_close| > |close-open| → "GAP".

    분봉 미수집 환경의 best-effort 근사. 주/월/분기봉은 의미가 없어 None.
    """
    if chart_interval != "1D" or idx <= 0:
        return None
    bar = bars[idx]
    prev_close = bars[idx - 1].close
    if prev_close <= 0:
        return None
    gap = abs(bar.open - prev_close)
    intraday = abs(bar.close - bar.open)
    if gap == 0 and intraday == 0:
        return None
    return "GAP" if gap > intraday else "INTRADAY"


def _cumulative_return(bars: List[StockBar], idx: int, n: int) -> Optional[float]:
    """spike 봉(idx) 종가 기준 +n봉 후 raw 누적 수익률(%). 미래 데이터 부족하면 None.

    봉 단위 무관 — 일봉이면 +n거래일, 주봉이면 +n주. benchmark 미차감(raw).
    """
    target_idx = idx + n
    if target_idx >= len(bars):
        return None
    base = bars[idx].close
    if base <= 0:
        return None
    return round((bars[target_idx].close / base - 1.0) * 100.0, 4)


def _detect_zscore_anomalies(
    bars: List[StockBar], chart_interval: str, ticker: str,
) -> List[AnomalyBarResponse]:
    """단일봉 z-score 탐지 (기존 로직 유지 + KR1 종목 군별 floor 적용)."""
    params = _PARAMS_BY_INTERVAL.get(chart_interval)
    if params is None:
        raise ValueError(f"Unsupported chart_interval: {chart_interval!r}")

    if len(bars) <= params.window + 1:
        return []

    returns = _compute_returns(bars)
    candidates: list[tuple[int, float, float]] = []  # (idx, return_pct, z_score)
    floor_abs = _floor_pct_for(chart_interval, ticker, params.floor_pct) / 100.0

    for i in range(params.window, len(returns)):
        window_slice = returns[i - params.window: i]
        try:
            sigma = statistics.stdev(window_slice)
        except statistics.StatisticsError:
            sigma = 0.0
        if math.isnan(sigma) or sigma < 0:
            sigma = 0.0

        # KR1 — z-score OR floor 결합. σ 가 0/극소여도 floor 만 통과하면 잡는다.
        threshold = max(params.k * sigma, floor_abs) if sigma > 0 else floor_abs
        r = returns[i]
        if abs(r) < threshold:
            continue

        z = r / sigma if sigma > 0 else 0.0
        candidates.append((i + 1, r * 100.0, z))

    # |z| 우선 → 동률(σ=0 케이스) 은 |return_pct| 큰 순으로 백업 정렬.
    candidates.sort(key=lambda x: (abs(x[2]), abs(x[1])), reverse=True)
    top = candidates[: params.max_count]

    return [
        AnomalyBarResponse(
            date=bars[idx].bar_date,
            type="zscore",
            return_pct=round(ret_pct, 4),
            z_score=round(z, 4),
            direction="up" if ret_pct > 0 else "down",
            close=round(bars[idx].close, 4),
            volume_ratio=_volume_ratio(bars, idx, params.window),
            time_of_day=_time_of_day(bars, idx, chart_interval),
            cumulative_return_1d=_cumulative_return(bars, idx, 1),
            cumulative_return_5d=_cumulative_return(bars, idx, 5),
            cumulative_return_20d=_cumulative_return(bars, idx, 20),
            causality=None,
        )
        for idx, ret_pct, z in top
    ]


def _detect_cumulative_anomalies(
    bars: List[StockBar], chart_interval: str,
) -> List[AnomalyBarResponse]:
    """KR2 — 5/20일 누적 윈도우 탐지기.

    임계값(±10% / ±15%) 이상으로 **처음 진입한 봉**만 마커. 다음 봉이 임계 안으로
    빠져나가면 trigger 가 재무장됨(재진입 시 재 마커). 임계 안에서 진동하는 작은
    fluctuation 은 무시되어 `잔잔한 연속 하락` 누적이 임계 넘어서는 시점만 잡힌다.

    1D 만 동작. 1W/1M/1Q 는 봉 자체가 길어 누적 의미가 약함 — 빈 리스트 반환.
    z-score 와의 dedup 은 호출자(`detect_anomalies`) 가 담당.
    """
    if chart_interval != "1D":
        return []
    if len(bars) <= 21:
        return []

    events: List[AnomalyBarResponse] = []
    # trigger 재무장 플래그. 직전 봉이 임계 밖이었으면 True.
    armed_5d = True
    armed_20d = True

    for i in range(5, len(bars)):
        prev = bars[i - 5].close
        if prev <= 0:
            armed_5d = True
            continue
        ret_5d = bars[i].close / prev - 1.0
        is_above_5d = abs(ret_5d) > _CUMULATIVE_5D_THRESHOLD
        if is_above_5d and armed_5d:
            events.append(
                AnomalyBarResponse(
                    date=bars[i].bar_date,
                    type="cumulative_5d",
                    return_pct=round(ret_5d * 100.0, 4),
                    z_score=0.0,
                    direction="up" if ret_5d > 0 else "down",
                    close=round(bars[i].close, 4),
                    volume_ratio=_volume_ratio(bars, i, 60),
                    time_of_day=_time_of_day(bars, i, chart_interval),
                    cumulative_return_1d=_cumulative_return(bars, i, 1),
                    cumulative_return_5d=_cumulative_return(bars, i, 5),
                    cumulative_return_20d=_cumulative_return(bars, i, 20),
                    causality=None,
                )
            )
        armed_5d = not is_above_5d

    for i in range(20, len(bars)):
        prev = bars[i - 20].close
        if prev <= 0:
            armed_20d = True
            continue
        ret_20d = bars[i].close / prev - 1.0
        is_above_20d = abs(ret_20d) > _CUMULATIVE_20D_THRESHOLD
        if is_above_20d and armed_20d:
            events.append(
                AnomalyBarResponse(
                    date=bars[i].bar_date,
                    type="cumulative_20d",
                    return_pct=round(ret_20d * 100.0, 4),
                    z_score=0.0,
                    direction="up" if ret_20d > 0 else "down",
                    close=round(bars[i].close, 4),
                    volume_ratio=_volume_ratio(bars, i, 60),
                    time_of_day=_time_of_day(bars, i, chart_interval),
                    cumulative_return_1d=_cumulative_return(bars, i, 1),
                    cumulative_return_5d=_cumulative_return(bars, i, 5),
                    cumulative_return_20d=_cumulative_return(bars, i, 20),
                    causality=None,
                )
            )
        armed_20d = not is_above_20d

    return events


def detect_anomalies(
    bars: List[StockBar], chart_interval: str, ticker: str = "",
) -> List[AnomalyBarResponse]:
    """순수 함수 — bars + interval + ticker → 이상치 봉 목록.

    z-score 결과 + 누적 윈도우 결과를 dedup 정책에 따라 합쳐 반환:
    - 같은 날에 z-score 와 누적이 모두 잡히면 **z-score 우선**(중복 마커 회피).
    - 같은 날에 5일 누적과 20일 누적이 모두 잡히면 **20일 우선**(더 큰 패턴).
    날짜 오름차순으로 정렬해 프론트 렌더 편의 확보.

    `ticker` default `""` 는 backward-compat — 종목 군 분류 없이 미국(US) fallback.
    """
    zscore_events = _detect_zscore_anomalies(bars, chart_interval, ticker)
    cumulative_events = _detect_cumulative_anomalies(bars, chart_interval)

    by_date: Dict[object, AnomalyBarResponse] = {}
    # z-score 우선 → 먼저 채움.
    for ev in zscore_events:
        by_date[ev.date] = ev
    # 20일 우선 → 5일 추가 후 20일 덮어쓰기 순서.
    for ev in cumulative_events:
        if ev.date in by_date:
            existing = by_date[ev.date]
            if existing.type == "zscore":
                continue  # z-score 우선 정책
            if existing.type == "cumulative_5d" and ev.type == "cumulative_20d":
                by_date[ev.date] = ev  # 20일 우선
            continue
        by_date[ev.date] = ev

    merged = sorted(by_date.values(), key=lambda e: e.date)
    return merged


class DetectAnomalyBarsUseCase:
    """엔드포인트에서 호출하는 UseCase 래퍼."""

    def __init__(self, stock_bars_port: StockBarsPort):
        self._stock_bars_port = stock_bars_port

    async def execute(
        self, ticker: str, chart_interval: str
    ) -> AnomalyBarsResponse:
        _, bars = await self._stock_bars_port.fetch_stock_bars(
            ticker=ticker, chart_interval=chart_interval
        )
        events = detect_anomalies(bars, chart_interval, ticker)
        zscore_n = sum(1 for e in events if e.type == "zscore")
        cum5_n = sum(1 for e in events if e.type == "cumulative_5d")
        cum20_n = sum(1 for e in events if e.type == "cumulative_20d")
        logger.info(
            "[DetectAnomalyBars] ticker=%s chart_interval=%s bars=%d anomalies=%d "
            "(zscore=%d cumulative_5d=%d cumulative_20d=%d)",
            ticker, chart_interval, len(bars), len(events),
            zscore_n, cum5_n, cum20_n,
        )
        return AnomalyBarsResponse(
            ticker=ticker,
            chart_interval=chart_interval,
            count=len(events),
            events=events,
        )
