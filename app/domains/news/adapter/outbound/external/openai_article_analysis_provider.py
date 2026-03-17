import json

from openai import AsyncOpenAI

from app.common.exception.app_exception import AppException
from app.domains.news.application.port.article_analysis_provider import (
    ArticleAnalysisProvider,
)
from app.domains.news.application.response.analyze_article_response import (
    AnalyzeArticleResponse,
)

_SYSTEM_PROMPT = """You are a financial news analyst.
Given a news article, respond ONLY with a valid JSON object (no markdown, no explanation) in this exact format:
{
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "sentiment": "positive" | "negative" | "neutral",
  "sentiment_score": <float between -1.0 and 1.0>
}
Rules:
- keywords: extract 3~7 core keywords from the article
- sentiment: overall tone of the article
- sentiment_score: -1.0 is most negative, 0.0 is neutral, 1.0 is most positive"""


class OpenAIArticleAnalysisProvider(ArticleAnalysisProvider):
    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(api_key=api_key)

    async def analyze(self, article_id: int, content: str) -> AnalyzeArticleResponse:
        try:
            response = await self._client.responses.create(
                model="gpt-5-mini",
                input=[
                    {"role": "developer", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
            )
            raw = response.output_text.strip()
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise AppException(status_code=502, message="분석 결과를 파싱할 수 없습니다.")
        except Exception as e:
            raise AppException(status_code=502, message=f"OpenAI 분석 중 오류가 발생했습니다: {str(e)}")

        return AnalyzeArticleResponse(
            article_id=article_id,
            keywords=data["keywords"],
            sentiment=data["sentiment"],
            sentiment_score=float(data["sentiment_score"]),
        )
