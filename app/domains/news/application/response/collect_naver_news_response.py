from pydantic import BaseModel


class CollectedNewsItemResponse(BaseModel):
    title: str
    description: str | None
    url: str
    published_at: str | None
    keyword: str

    model_config = {"from_attributes": True}


class CollectNaverNewsResponse(BaseModel):
    total_collected: int
    skipped_duplicates: int
    items: list[CollectedNewsItemResponse]
