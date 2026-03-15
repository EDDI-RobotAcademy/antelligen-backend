from fastapi import APIRouter

from app.domains.post.adapter.inbound.api.post_router import router as post_router
from app.domains.stock.adapter.inbound.api.stock_router import router as stock_router

router = APIRouter(prefix="/api")

router.include_router(post_router)
router.include_router(stock_router)
