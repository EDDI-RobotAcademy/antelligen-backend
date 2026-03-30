import json
import time

from openai import AsyncOpenAI

from app.common.exception.app_exception import AppException
from app.domains.agent.application.port.finance_agent_provider import (
    FinanceAgentProvider,
)
from app.domains.agent.application.response.investment_signal_response import (
    InvestmentSignalResponse,
)
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.stock.application.response.stock_collection_response import (
    StockCollectionResponse,
)

_SYSTEM_PROMPT = """You are a Korean equity financial analysis agent.
You will receive a user's question and structured stock collection data including DART financial ratios.
Respond ONLY with a valid JSON object in this exact schema:
{
  "signal": "bullish" | "bearish" | "neutral",
  "confidence": <float between 0.0 and 1.0>,
  "summary": "<one concise Korean sentence>",
  "key_points": ["<Korean bullet 1>", "<Korean bullet 2>", "<Korean bullet 3>"]
}

Rules:
- Base the answer only on the provided stock data.
- Consider DART financial ratios (ROE, ROA, debt_ratio) for deeper analysis when available.
- ROE (자기자본이익률): Higher is better, typically >10% is good.
- ROA (총자산이익률): Higher is better, typically >5% is good.
- debt_ratio (부채비율): Lower is better, typically <100% is healthy.
- If the data is limited, stay conservative and prefer "neutral".
- summary must be short, clear, and written in Korean.
- key_points must contain exactly 3 Korean strings.
- Do not include markdown or any text outside the JSON object."""


class OpenAIFinanceAgentProvider(FinanceAgentProvider):
    def __init__(self, api_key: str, model: str):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def analyze(
        self,
        *,
        user_query: str,
        stock_data: StockCollectionResponse,
    ) -> SubAgentResponse:
        started_at = time.perf_counter()

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "developer", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": self._build_user_prompt(
                            user_query=user_query,
                            stock_data=stock_data,
                        ),
                    },
                ],
            )
            payload = json.loads(response.output_text.strip())
        except json.JSONDecodeError as exc:
            raise AppException(
                status_code=502,
                message="재무분석 응답을 파싱할 수 없습니다.",
            ) from exc
        except Exception as exc:
            raise AppException(
                status_code=502,
                message=f"OpenAI 재무분석 중 오류가 발생했습니다: {str(exc)}",
            ) from exc

        execution_time_ms = int((time.perf_counter() - started_at) * 1000)
        signal = InvestmentSignalResponse(
            agent_name="finance",
            ticker=stock_data.ticker,
            signal=payload["signal"],
            confidence=float(payload["confidence"]),
            summary=payload["summary"],
            key_points=payload["key_points"],
        )

        return SubAgentResponse.success_with_signal(
            signal=signal,
            data=self._build_result_data(stock_data),
            execution_time_ms=execution_time_ms,
        )

    def _build_user_prompt(
        self,
        *,
        user_query: str,
        stock_data: StockCollectionResponse,
    ) -> str:
        financial_info = (
            stock_data.financial_information.model_dump(mode="json")
            if stock_data.financial_information
            else {}
        )

        dart_ratios = (
            stock_data.dart_financial_ratios.model_dump(mode="json")
            if stock_data.dart_financial_ratios
            else {}
        )

        return json.dumps(
            {
                "user_query": user_query,
                "stock": {
                    "ticker": stock_data.ticker,
                    "stock_name": stock_data.stock_name,
                    "market": stock_data.market,
                    "collected_types": stock_data.collected_types,
                    "financial_information": financial_info,
                    "dart_financial_ratios": dart_ratios,
                    "document_text": stock_data.document_text,
                    "reference_url": stock_data.metadata.reference_url,
                    "collected_at": stock_data.metadata.collected_at.isoformat(),
                },
            },
            ensure_ascii=False,
        )

    def _build_result_data(
        self,
        stock_data: StockCollectionResponse,
    ) -> dict:
        financial_info = stock_data.financial_information
        dart_ratios = stock_data.dart_financial_ratios

        return {
            "ticker": stock_data.ticker,
            "stock_name": stock_data.stock_name,
            "market": stock_data.market,
            "current_price": financial_info.current_price if financial_info else None,
            "currency": financial_info.currency if financial_info else None,
            "market_cap": financial_info.market_cap if financial_info else None,
            "pe_ratio": financial_info.pe_ratio if financial_info else None,
            "dividend_yield": financial_info.dividend_yield if financial_info else None,
            "roe": dart_ratios.roe if dart_ratios else None,
            "roa": dart_ratios.roa if dart_ratios else None,
            "debt_ratio": dart_ratios.debt_ratio if dart_ratios else None,
            "fiscal_year": dart_ratios.fiscal_year if dart_ratios else None,
            "reference_url": stock_data.metadata.reference_url,
            "collected_at": stock_data.metadata.collected_at.isoformat(),
        }
