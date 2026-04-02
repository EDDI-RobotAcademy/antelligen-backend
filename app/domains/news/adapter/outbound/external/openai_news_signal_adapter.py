import json

from openai import AsyncOpenAI

from app.common.exception.app_exception import AppException
from app.domains.agent.application.response.investment_signal_response import (
    InvestmentSignal,
    InvestmentSignalResponse,
)
from app.domains.news.application.port.news_signal_analysis_port import NewsSignalAnalysisPort
from app.domains.news.domain.entity.collected_news import CollectedNews

_SYSTEM_PROMPT = """당신은 한국 주식 시장 뉴스 감성 분석 전문가입니다.
기업 관련 뉴스 헤드라인과 요약을 바탕으로 투자 감성을 분석합니다.

분석 지침:
1. 최근 기사일수록 더 중요하게 반영하세요.
2. 단순 사실 보도보다 실적·계약·규제·인사 등 투자 판단에 영향을 주는 뉴스를 우선시하세요.
3. key_points는 "구체적 사실(날짜/수치 포함) + 투자 의미" 형태로 작성하세요.
4. 긍정·부정 신호가 혼재할 경우 전체 균형을 반영하여 neutral로 판단하세요.
5. confidence는 뉴스 수, 신호 일관성, 최신성을 종합하여 결정하세요.
   (기사 5건 이상 + 신호 일관 → 0.7↑, 기사 적거나 혼재 → 0.4~0.6)

반드시 아래 JSON 형식으로만 응답하세요 (마크다운, 설명 금지):
{
  "signal": "bullish" | "bearish" | "neutral",
  "confidence": <float 0.0~1.0>,
  "summary": "<투자 관점 2~3문장 한국어 요약, 주요 뉴스 흐름과 투자 시사점 포함>",
  "key_points": ["<날짜/수치 근거 포함 포인트>", ...]
}"""

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
