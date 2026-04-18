import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from app.domains.study.application.port.out.video_learning_llm_port import VideoLearningLlmPort
from app.domains.study.domain.entity.study_video_input import StudyVideoInput
from app.domains.study.domain.entity.video_learning import StockInsight, VideoLearning
from app.domains.study.domain.value_object.investment_view import InvestmentView
from app.domains.study.domain.value_object.learning_program_type import LearningProgramType
from app.infrastructure.external.openai_responses_client import OpenAIResponsesClient

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_CHARS = 12000

_INSTRUCTIONS = """\
당신은 한국 주식 교육 영상을 학습하여 구조화된 지식을 추출하는 분석 어시스턴트입니다.
입력은 하나의 유튜브 영상의 제목, 설명, 자막 전문입니다.
당신의 임무:
1) 영상의 핵심 요약을 한국어로 3~6문장으로 작성합니다. 유튜브 프리미엄의 "요약" 기능처럼 시청자가 영상을 보지 않고도 핵심 흐름을 이해하도록 작성합니다.
2) 영상에서 언급된 개별 종목(주식)에 대해 아래 구조로 인사이트를 뽑습니다:
   - stock_name (한국어 종목명 그대로, 특정 종목이 아니면 생략)
   - investment_view: 매수 | 관망 | 매도 | 지켜보기 | 불명 중 하나
   - key_claims: 영상에서 주장한 핵심 논지 (문자열 배열, 최대 5개)
   - evidences: 해당 주장을 뒷받침하는 구체적 근거 (문자열 배열, 최대 5개)
3) 자막에 근거하지 않은 내용을 지어내지 마십시오. 불확실하면 investment_view 를 "불명"으로 설정합니다.

반드시 다음 JSON 스키마에 맞춰 응답합니다. 다른 머리말/꼬리말/코드펜스를 포함하지 마십시오.

{
  "summary": "...",
  "stock_insights": [
    {
      "stock_name": "...",
      "investment_view": "매수|관망|매도|지켜보기|불명",
      "key_claims": ["..."],
      "evidences": ["..."]
    }
  ]
}
"""


class OpenAIVideoLearningAdapter(VideoLearningLlmPort):
    def __init__(self, client: OpenAIResponsesClient):
        self._client = client

    async def learn(self, video: StudyVideoInput) -> VideoLearning:
        payload = self._build_input_payload(video)
        print(
            f"[study.llm] OpenAI Responses 요청 video_id={video.video_id} "
            f"payload_len={len(payload)}"
        )
        result = await self._client.create(
            instructions=_INSTRUCTIONS,
            input_text=payload,
        )
        print(
            f"[study.llm] OpenAI Responses 응답 video_id={video.video_id} "
            f"model={result.model} output_len={len(result.output_text)}"
        )
        parsed = self._parse(result.output_text)
        print(
            f"[study.llm] JSON 파싱 완료 video_id={video.video_id} "
            f"stocks={len(parsed.get('stock_insights', []) or [])}"
        )

        program_type = LearningProgramType.classify(video.title, video.description)
        return VideoLearning(
            video_id=video.video_id,
            title=video.title,
            channel_name=video.channel_name,
            channel_id=video.channel_id,
            published_at=video.published_at,
            collected_at=video.collected_at or datetime.now(),
            program_type=program_type,
            summary=parsed.get("summary", ""),
            stock_insights=self._build_stock_insights(parsed.get("stock_insights", [])),
        )

    @staticmethod
    def _build_input_payload(video: StudyVideoInput) -> str:
        transcript = (video.transcript or "").strip()
        if len(transcript) > MAX_TRANSCRIPT_CHARS:
            transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n...(자막 truncated)..."
        return (
            f"[영상 제목]\n{video.title}\n\n"
            f"[영상 설명]\n{(video.description or '').strip() or '(없음)'}\n\n"
            f"[업로드일]\n{video.published_at.isoformat()}\n\n"
            f"[자막]\n{transcript or '(자막 없음)'}\n"
        )

    @staticmethod
    def _parse(raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                logger.warning("[study.learn] LLM 응답 JSON 파싱 실패: %s", text[:300])
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("[study.learn] LLM JSON 재파싱 실패: %s", text[:300])
                return {}

    @staticmethod
    def _build_stock_insights(raw_list: Any) -> List[StockInsight]:
        if not isinstance(raw_list, list):
            return []
        insights: List[StockInsight] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            name = str(item.get("stock_name", "")).strip()
            if not name:
                continue
            claims = [
                str(c).strip()
                for c in (item.get("key_claims") or [])
                if str(c).strip()
            ][:5]
            evidences = [
                str(e).strip()
                for e in (item.get("evidences") or [])
                if str(e).strip()
            ][:5]
            insights.append(
                StockInsight(
                    stock_name=name,
                    investment_view=InvestmentView.parse(str(item.get("investment_view", ""))),
                    key_claims=claims,
                    evidences=evidences,
                )
            )
        return insights
