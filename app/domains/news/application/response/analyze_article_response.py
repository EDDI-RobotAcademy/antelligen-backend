from pydantic import BaseModel


class AnalyzeArticleResponse(BaseModel):
    article_id: int
    keywords: list[str]
    sentiment: str  # "positive" | "negative" | "neutral"
    sentiment_score: float  # -1.0 (매우 부정) ~ 1.0 (매우 긍정)
