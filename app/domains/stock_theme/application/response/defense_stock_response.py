from pydantic import BaseModel


class DefenseStockItem(BaseModel):
    id: int
    name: str
    code: str
    themes: list[str]


class DefenseStockListResponse(BaseModel):
    total: int
    items: list[DefenseStockItem]
