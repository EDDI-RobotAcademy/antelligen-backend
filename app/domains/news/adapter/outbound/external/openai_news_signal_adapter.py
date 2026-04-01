import json

from openai import AsyncOpenAI

from app.common.exception.app_exception import AppException
from app.domains.agent.application.response.investment_signal_response import (
    InvestmentSignal,
    InvestmentSignalResponse,
)
from app.domains.news.application.port.news_signal_analysis_port import NewsSignalAnalysisPort
from app.domains.news.domain.entity.collected_news import CollectedNews

_SYSTEM_PROMPT = """You are a Korean stock market news sentiment analyst.
Given news article headlines and summaries about a company, analyze the overall investment sentiment.

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "signal": "bullish" | "bearish" | "neutral",
  "confidence": <float 0.0~1.0>,
  "summary": "<1-2 sentence summary in Korean>",
  "key_points": ["<point1 in Korean>", "<point2 in Korean>", ...]
}

Rules:
- signal: overall investment sentiment based on the news
- confidence: certainty of the signal (0.0 = uncertain, 1.0 = very certain)
- summary: brief overall assessment in Korean (1-2 sentences)
- key_points: 2~5 key findings from the articles in Korean"""

_MAX_ARTICLES = 10


class OpenAINewsSignalAdapter(NewsSignalAnalysisPort):
    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def analyze(
        self, ticker: str, company_name: str, articles: list[CollectedNews]
    ) -> InvestmentSignalResponse:
        news_text = self._format_articles(company_name, articles)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": news_text},
                ],

            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise AppException(status_code=502, message="GPT 뉴스 분석 결과를 파싱할 수 없습니다.")
        except Exception as e:
            raise AppException(status_code=502, message=f"GPT 뉴스 분석 중 오류: {str(e)}")

        return InvestmentSignalResponse(
            agent_name="news",
            ticker=ticker,
            signal=InvestmentSignal(data["signal"]),
            confidence=float(data["confidence"]),
            summary=data["summary"],
            key_points=data["key_points"],
        )

    @staticmethod
    def _format_articles(company_name: str, articles: list[CollectedNews]) -> str:
        target = articles[:_MAX_ARTICLES]
        lines = [f"[{company_name} 관련 뉴스 {len(target)}건]\n"]
        for i, article in enumerate(target, 1):
            lines.append(f"{i}. {article.title}")
            if article.description:
                lines.append(f"   {article.description}")
            lines.append(f"   (발행: {article.published_at})\n")
        return "\n".join(lines)
