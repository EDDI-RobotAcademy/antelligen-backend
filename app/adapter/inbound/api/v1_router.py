# /api/v1 공통 라우터 집합
# 팀원 가이드: 새 도메인 라우터를 만들면 이 파일에 include_router만 추가하면 된다.
#
# 추가 예시:
#   from app.domains.news.adapter.inbound.api.news_router import router as news_router
#   api_v1_router.include_router(news_router)

from fastapi import APIRouter

from app.domains.post.adapter.inbound.api.post_router import router as post_router
from app.domains.stock.adapter.inbound.api.stock_router import router as stock_router

# 모든 API는 /api/v1 prefix를 가진다.
api_v1_router = APIRouter(prefix="/api/v1")

# --- 도메인 라우터 등록 ---
api_v1_router.include_router(post_router)       # POST: /api/v1/post/...
api_v1_router.include_router(stock_router)      # STOCK: /api/v1/stock/...
# api_v1_router.include_router(news_router)     # 뉴스 에이전트 완성 시 여기 추가
# api_v1_router.include_router(finance_router)  # 재무 에이전트
# api_v1_router.include_router(disclosure_router)  # 공시 에이전트
