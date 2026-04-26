# ADR-0002: Event Impact (Abnormal Return) 별도 Aggregate 분리

## Status

Accepted — 2026-04-26 (PR1 d3e6f44 + PR2 990ca2a + PR3 9b27b32)

## Context

`EventImportanceService` 가 LLM 추정만으로 이벤트 중요도를 매기는 한계가 있었다. 시점
명확 사건(공시·기업행위·매크로) 후 **종목이 시장 대비 얼마나 움직였는지** (abnormal
return, AR) 같은 정량 시그널이 입력에 부재했다.

코드 전수 조사 결과 (2026-04-26):

- `nasdaq_bars` 테이블은 `^IXIC` 인덱스 일봉만 적재. 종목 단위 OHLCV 영구 저장 없음.
  `YahooFinanceStockClient` 가 매 timeline 호출마다 yfinance 실시간 fetch.
- grep `abnormal | excess return | alpha | benchmark` = **0 hit** — abnormal return
  계산 로직 자체 부재.
- `causality_agent.gather_situation_node` 도 동일하게 yfinance 직접 호출.
- `_INDEX_REGION` / `_ETF_REGION` dict 가 history_agent_usecase 안에 박혀 있어 벤치마크
  매핑이 application layer에 잠겨 있음.

목표:

1. 종목 일봉을 PostgreSQL에 영구 적재
2. 이벤트별 ±5/±20거래일 abnormal return 계산 + 영속화
3. 응답 + Importance prompt 통합으로 정량 시그널화
4. causality_agent 도 같은 캐시 레이어 재사용해 yfinance 호출 절감

## Decision

### 1. 도메인 배치 — `app/domains/stock/market_data/` sub-package

`stock` 도메인 내부에 sub-package 로 격리. cross-domain 사용처(history_agent /
causality_agent / dashboard) 모두 application port 통해 접근. 추후 top-level
`market_data` 도메인으로 승격 가능 (import 경로 sed 만).

대안 비교:

- **history_agent 내부**: cross-domain import 유발, 비대화. 거부.
- **dashboard 내부**: nasdaq_bars 단일 ticker 가정과 충돌. 거부.
- **top-level `market_data` 즉시 분리**: PR diff 폭증. 연기.

### 2. Storage — EventEnrichment 컬럼 확장이 아니라 별도 Aggregate

새 테이블 `event_impact_metrics`:
- UK: `(ticker, event_date, event_type, detail_hash, pre_days, post_days)`
- `detail_hash` 는 `history_agent.compute_detail_hash` 와 동일 알고리즘 → enrichment
  행과 join 가능하지만 별도 row.

이유:
- 캐시 무효화 차원이 다르다. enrichment 는 `classifier_version`, AR 은 yfinance
  adjusted close 반영 시점인 `bars_data_version` 에 종속.
- UK 차원이 다르다. enrichment 5-tuple vs AR 6-tuple (윈도우 차원 추가).
- enrichment 비대화 시 LLM 분류 변경이 AR 무효화로 의도치 않게 전파됨 — 우발적 결합.

### 3. AR 계산 — Domain Service (Port 아님)

`BenchmarkResolver` + `AbnormalReturnCalculator` 는 **순수 함수**라 IO 부재.
CLAUDE.md "Domain은 ORM/HTTP import 금지 + Application은 Port/Adapter로만" 규칙상
순수 계산은 Port 추상화로 감추면 오히려 Domain rule 을 가린다. Port 는 IO 있는
인터페이스에만 사용 (`DailyBarRepositoryPort`, `DailyBarFetcherPort`,
`EventImpactMetricRepositoryPort`).

### 4. 윈도우 — ±5d / ±20d 둘 다 저장, 프론트는 5d 우선 노출

- pre = -1 (이벤트 직전 거래일 종가)
- post = +5 / +20 (이벤트 후 N번째 거래일 종가)
- 백필 비용은 동일 (양 윈도우 한 번에 계산)
- 프론트는 5d 를 메인 시그널로, 20d 는 보조 표시. 학술적 event study 의 [-1, +5]
  / [-1, +20] CAR 윈도우와 비슷한 의미.

### 5. 벤치마크 — region 별 단일

- `US` → `^GSPC` (S&P 500)
- `KR` → `^KS11` (KOSPI)
- 비-EQUITY (INDEX/ETF/MUTUALFUND) → None — `BENCHMARK_MISSING` 으로 mark
- 섹터별(GICS) 정밀화는 follow-up.

### 6. AR 계산 시점 — daily batch (KST 08:00)

- `event_date <= today − 21 일` 조건 — ±20d 미래 데이터 가용성 확보 후 처리
- daily_bars 적재 잡(KST 07:30) 직후 실행
- 이벤트 검출 시점 즉시 계산은 미래 데이터 부재로 INSUFFICIENT_DATA 빈발 — 거부

### 7. Importance 통합 — LLM prompt 텍스트 주입 (numeric weighting 미사용)

`_build_line` / `_build_line_v2` 에 `ar_5d=+3.21%` 텍스트 추가. flag
`event_impact_in_importance_prompt` (default true). 분포 안정화 후 numeric
weighting (예: `score += 0.05·sign(ar)`) 으로 격상은 별도 ADR.

### 8. causality_agent OHLCV — 같은 캐시 레이어 재사용 (feature flag)

`CachedDailyBarFetcher(repository, fallback)` decorator 도입.
`gather_situation_node._fetch_ohlcv_sync` 를 flag `causality_use_cached_bars`
(default false) 로 cached 경로 활성. DB 적중 시 yfinance 호출 0회.

### 9. 데이터 일관성 — sliding window 재적재 + bars_data_version

매일 KST 07:30 잡이 `period="5d"` 로 직전 5거래일을 재 upsert (`auto_adjust=True`
adjusted close 기준). split corporate action 발생 시 `bars_data_version` 도 새
적재 시점 토큰으로 갱신. 명시적 split invalidation 핸들러는 follow-up.

## Consequences

### 좋은 점

- LLM 부산물 캐시(enrichment) 와 정량 시그널(impact) 의 책임 분리
- AR 재계산 시 enrichment 무손상 (cascade invalidation 없음)
- causality_agent / history_agent / 신규 batch job 모두 단일 fetcher 인터페이스 사용
- Port 추상화로 yfinance → polygon/alpha vantage 등 source swap 용이
- timeline 응답에 정량 시그널 노출 → 프론트 카드에 abnormal return 배지 (PR4)

### 트레이드오프

- 별도 테이블이라 응답 빌드 시 join 1회 비용 증가 (작음 — 같은 PG 인스턴스)
- 비-EQUITY (ETF holdings 의 inner equity 등) 는 현재 BENCHMARK_MISSING 처리 →
  ETF 응답 카드는 AR 미노출. 이는 AR job 이 `event_enrichments.ticker` (response
  ticker) 기준으로 조회하기 때문 — constituent_ticker 로 별도 조회는 follow-up.
- daily batch 라 21일 미만 신규 이벤트는 AR 미노출 — 운영상 허용 범위로 판단

### 위험

- yfinance split 후 historical price 조정으로 과거 AR 가 stale 가능 — `bars_data_version`
  비교로 trigger 감지하지만 자동 재계산 스케줄러는 follow-up.
- 시장 벤치마크 단일 매핑 (^GSPC) 가 모든 US 종목에 적합하지 않을 수 있음 (소형주는
  Russell 2000 등 벤치마크가 더 적합). 분포 모니터링 후 결정.

## Follow-up

- 섹터별 벤치마크 매핑 (GICS sector → 적합 ETF/index)
- Split 자동 재계산 트리거 (yfinance corporate event split 감지 → bars_data_version
  invalidation → AR 재계산)
- ETF holdings 에 대해 constituent_ticker 기준 AR 계산 (PendingEventForImpactQueryImpl
  확장)
- 분포 안정화 후 importance prompt 의 텍스트 주입을 numeric weighting 으로 격상 ADR
- ANOMALY_BAR 자체에 대한 AR 정의 (가격 이벤트라 pre/post 의미 다름)

## 관련 PR / 파일

- PR1 `d3e6f44` — daily_bars OHLCV 적재 인프라
- PR2 `990ca2a` — event_impact_metrics + AR 계산 파이프라인
- PR3 `9b27b32` — timeline 응답 + Importance + causality 캐시 전환
- PR4 antelligen-frontend `118fa33` — 카드 ▾ expand 영역 ARBadge

핵심 파일:
- `app/domains/stock/market_data/domain/service/abnormal_return_calculator.py`
- `app/domains/stock/market_data/domain/service/benchmark_resolver.py`
- `app/domains/stock/market_data/domain/entity/event_impact_metric.py`
- `app/domains/stock/market_data/application/usecase/compute_event_impact_usecase.py`
- `app/infrastructure/scheduler/ar_calculation_jobs.py`
- `alembic/versions/0006_create_event_impact_metrics.py`
