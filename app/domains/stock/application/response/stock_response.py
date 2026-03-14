from pydantic import BaseModel


class StockResponse(BaseModel):
    ticker: str
    stock_name: str
    market: str
