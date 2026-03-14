from fastapi import APIRouter, HTTPException

from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import StockRepositoryImpl
from app.domains.stock.application.response.stock_response import StockResponse
from app.domains.stock.application.usecase.get_stock_usecase import GetStockUseCase

router = APIRouter(prefix="/stock", tags=["Stock"])


@router.get("/{ticker}", response_model=StockResponse)
async def get_stock(ticker: str):
    repository = StockRepositoryImpl()
    usecase = GetStockUseCase(repository)
    result = await usecase.execute(ticker)
    if result is None:
        raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {ticker}")
    return result
