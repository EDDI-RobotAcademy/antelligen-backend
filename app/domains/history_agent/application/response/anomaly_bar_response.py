from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class AnomalyBarResponse(BaseModel):
    """차트에 마커로 표시할 이상치 봉 1건.

    - `type`: 탐지기 분류. 다층 탐지로 확장됨.
      "zscore"              — 단일봉 z-score (기존 ★)
      "cumulative_5d"       — 5거래일 누적 ±10% 진입 봉 (🔻)
      "cumulative_20d"      — 20거래일 누적 ±15% 진입 봉 (📉)
      "drawdown_start"      — 60봉 고점 대비 -10% 첫 진입 봉 (🔽)
      "drawdown_recovery"   — drawdown 구간에서 -3% 회복 봉 (🔼)
      "volatility_cluster"  — 5거래일 이내 |r|>5% 큰 변동 2건 이상 묶음의 첫 봉 (⚡)
      backward-compat 위해 default "zscore".
    - `cluster_size`/`cluster_end_date`: KR5 — 변동성 클러스터 메타.
      type="volatility_cluster" 일 때만 채워짐. 클러스터 구간 시각화에 사용.
    - `sigma_method`: KR4 디버그 — z-score 계산에 사용한 σ 방식.
      "stdev"  — 기존 statistics.stdev (default)
      "stable" — 안정 구간(|r|<3%) stdev (이상치 제외)
      "mad"    — Median Absolute Deviation × 1.4826
      누적/Drawdown 탐지에선 None (z-score 무관).
    - `return_pct`: type 별 수익률(%). zscore=직전 봉 대비 / cumulative_*=N일 누적.
    - `z_score`: `(return_pct/100 - μ) / σ`. 누적 탐지에선 0.0 으로 채움(의미 없음).
    - `direction`: `"up"` | `"down"` — 프론트 색 구분.
    - `volume_ratio`: σ window 평균 거래량 대비 배수. 평균이 0/누락이면 None.
    - `time_of_day`: 일봉(1D)에서만 채워지는 갭/장중 근사 — "GAP" | "INTRADAY".
      |open-prev_close| > |close-open| 이면 GAP. 분봉 미수집 환경의 best-effort 근사.
      일봉 외(주/월/분기봉) 또는 prev close 부재 시 None.
    - `cumulative_return_1d/5d/20d`: spike 봉 종가 기준 +N봉 후 raw 누적 수익률(%).
      봉 단위 무관 — 일봉이면 +N거래일, 주봉이면 +N주. benchmark 미차감(raw).
      bars 배열에 충분한 미래 데이터가 없으면 None.
    - `causality`: 초기엔 null. 마커 클릭 시 `/anomaly-bars/{ticker}/{date}/causality`
      엔드포인트가 lazy-fetch 한다.
    """
    date: date
    type: str = "zscore"
    return_pct: float
    z_score: float
    direction: str
    close: float
    volume_ratio: Optional[float] = None
    time_of_day: Optional[str] = None
    cumulative_return_1d: Optional[float] = None
    cumulative_return_5d: Optional[float] = None
    cumulative_return_20d: Optional[float] = None
    sigma_method: Optional[str] = None
    cluster_size: Optional[int] = None
    cluster_end_date: Optional[date] = None
    causality: Optional[str] = None


class AnomalyBarsResponse(BaseModel):
    ticker: str
    chart_interval: str
    count: int
    events: List[AnomalyBarResponse]
