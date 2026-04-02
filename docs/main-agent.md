# 메인 에이전트 개발 문서

## 개요

뉴스 · 공시 · 재무 서브에이전트를 **병렬 호출**하여 종합 투자 시그널과 LLM 분석 요약을 반환하는 오케스트레이터 에이전트입니다.

---

## 아키텍처

```
POST /api/v1/agent/query
        │
        ▼
ProcessAgentQueryUseCase
        ├─ PostgreSQL 캐시 확인 (1시간 이내 결과 재사용)
        ├─ asyncio.gather() → 뉴스 / 공시 / 재무 서브에이전트 병렬 호출
        ├─ 시그널 가중 집계 (bullish/bearish/neutral + confidence)
        ├─ OpenAISynthesisClient → LLM 종합 요약
        └─ PostgreSQL 저장 → 응답 반환
```

**주요 파일 위치** (`app/domains/agent/` 기준)

| 역할 | 파일 |
|------|------|
| 라우터 | `adapter/inbound/api/agent_router.py` |
| UseCase | `application/usecase/process_agent_query_usecase.py` |
| LLM 종합 | `adapter/outbound/external/openai_synthesis_client.py` |
| 뉴스 어댑터 | `adapter/outbound/external/news_sub_agent_adapter.py` |
| 공시 어댑터 | `adapter/outbound/external/disclosure_sub_agent_adapter.py` |
| 재무 어댑터 | `adapter/outbound/external/finance_sub_agent_adapter.py` |
| DB 저장소 | `adapter/outbound/persistence/integrated_analysis_repository_impl.py` |
| ORM | `infrastructure/orm/integrated_analysis_orm.py` |

---

## 엔드포인트 스펙

### POST /api/v1/agent/query

> 인증 필수: 쿼리 파라미터 `?token=`, 쿠키 `user_token`, 또는 `Authorization: Bearer` 헤더

**요청**
```json
{
  "ticker": "005930",
  "query": "삼성전자 투자해도 될까요?",
  "session_id": "(선택)"
}
```

**응답 주요 필드**
```json
{
  "data": {
    "session_id": "uuid",
    "result_status": "success | partial_failure | failure",
    "answer": "LLM 종합 요약",
    "agent_results": [
      {
        "agent_name": "news | disclosure | finance",
        "status": "success | no_data | error",
        "signal": "bullish | bearish | neutral",
        "confidence": 0.0~1.0,
        "summary": "에이전트 요약",
        "key_points": ["..."],
        "execution_time_ms": 10378
      }
    ],
    "total_execution_time_ms": 13026
  }
}
```

**응답 시간 참고**
- 캐시 히트 (동일 종목 1시간 이내 재요청): ~1초
- 뉴스 에이전트: 8~12초
- 공시 에이전트: 캐시 히트 ~500ms / LangGraph RAG 7~20초
- 재무 에이전트: 캐시 히트 ~1초 / 첫 분석 10초
- **신규 종목 첫 요청**: 데이터 자동 수집으로 40~60초 소요

---

### GET /api/v1/agent/history

> 인증 필수

**쿼리 파라미터**: `ticker` (필수), `limit` (기본 10, 최대 50)

**응답**: ticker 기준 최근 분석 이력 반환 (overall_signal, confidence, summary, key_points, created_at 포함)

---

## 시그널 집계 로직

`score = Σ(signal_score × confidence) / Σ(confidence)`

- bullish = +1.0 / neutral = 0.0 / bearish = -1.0
- score > 0.2 → bullish / score < -0.2 → bearish / 그 외 → neutral

---

## DB 테이블: `integrated_analysis_results`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER PK | 자동 증가 |
| `ticker` | VARCHAR(20) | 종목 코드 (인덱스) |
| `query` | TEXT | 사용자 질문 |
| `overall_signal` | VARCHAR(20) | bullish / bearish / neutral |
| `confidence` | FLOAT | 0.0 ~ 1.0 |
| `summary` | TEXT | LLM 종합 요약 |
| `key_points` | JSON | 핵심 포인트 리스트 |
| `sub_results` | JSON | 서브에이전트 결과 전체 |
| `execution_time_ms` | INTEGER | 처리 시간 (ms) |
| `created_at` | DATETIME | 생성 시각 |

캐시 전략: 동일 ticker 재조회 시 `created_at` 기준 **1시간 이내** 결과 재사용. 만료 시 서브에이전트 재호출 → 새 row INSERT.

---

## 재무 에이전트 자동 수집

벡터 DB에 데이터가 없는 종목 첫 요청 시 자동 수집:

```
analyze(ticker) → 404 (데이터 없음)
    └─ CollectStockDataUseCase.execute(ticker)
           (SerpAPI 기본 정보 + DART 재무비율 → 벡터 DB 저장)
    └─ 재시도 → 분석 완료
```

---

## 주요 설정값 (settings.py)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `openai_finance_agent_model` | gpt-5-mini | 재무 에이전트 모델 |
| `openai_embedding_model` | text-embedding-3-small | 임베딩 모델 |
| `finance_rag_top_k` | 3 | RAG 검색 청크 수 |
| `finance_analysis_cache_ttl_seconds` | 3600 | 재무 분석 캐시 TTL |

통합 분석 캐시 TTL: `ProcessAgentQueryUseCase.execute()` 내 `within_seconds=3600` 직접 수정.

---

## 분석 가능 종목 (8개)

뉴스 에이전트는 아래 8개 종목만 지원합니다. 공시·재무 에이전트는 모든 종목 지원.

> 새 종목 추가 시 `analyze_news_signal_usecase.py`의 `TICKER_TO_KEYWORDS`와 `collect_naver_news_usecase.py`의 `COLLECTION_KEYWORDS` 두 곳 모두 수정 필요.

| ticker | 종목명 | 질문 예시 |
|--------|--------|-----------|
| 005930 | 삼성전자 | "삼성전자 투자해도 될까요?" |
| 000660 | SK하이닉스 | "SK하이닉스 HBM 실적 기대되는데 투자해도 될까?" |
| 005380 | 현대차 | "현대차 전기차 전환 어떻게 보고 있어?" |
| 035420 | 네이버 | "네이버 AI 사업 성장 가능성 어때?" |
| 035720 | 카카오 | "카카오 지금 저점 매수 타이밍일까?" |
| 068270 | 셀트리온 | "셀트리온 바이오시밀러 전망은?" |
| 207940 | 삼성바이오로직스 | "삼성바이오로직스 장기 투자 괜찮을까?" |
| 005490 | 포스코 | "포스코홀딩스 2차전지 소재 사업 어때?" |
