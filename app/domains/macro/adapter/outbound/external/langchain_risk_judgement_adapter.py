import json
import logging
import re
from datetime import date
from typing import List, Optional

from app.domains.macro.application.port.out.risk_judgement_llm_port import (
    RiskJudgementLlmPort,
    RiskJudgementResult,
)
from app.domains.macro.domain.value_object.risk_status import RiskStatus
from app.infrastructure.external.openai_responses_client import OpenAIResponsesClient

logger = logging.getLogger(__name__)

_CONTEXTUAL_INSTRUCTIONS = (
    "당신은 한국 주식 시장을 관찰하는 매크로 분석 어시스턴트입니다.\n"
    "답변은 실제 전문 애널리스트가 설명하듯 정중하고 신뢰감 있는 한국어 문장으로 작성합니다.\n"
    "인용 문구가 아닌 자연스러운 설명체를 사용하되 과장하지 않습니다.\n"
    "reasons 배열은 한국어 문장으로 최대 3줄 이내이며 각 문장은 한 줄로 간결합니다.\n"
    "특정 유튜브 채널, 영상 제목, 저자명, 출처명을 답변에 노출하지 마십시오. "
    "참고 자료에서 얻은 지식이라도 출처를 언급하지 말고 '한국 시장 데이터', '최근 시장 흐름' 처럼 일반화된 표현을 사용합니다.\n"
    "판단 근거가 부족하면 status 를 \"UNKNOWN\" 으로 반환하고 reasons 에 사유를 적습니다.\n"
    "\n아래에 제공되는 학습 노트와 최근 7일간 참고 영상 요약을 참고하여 "
    "오늘({reference_date}) 기준 한국 시장이 Risk-on 인지 Risk-off 인지를 판단하십시오.\n"
    "제공된 컨텍스트 외의 사실을 지어내지 마십시오.\n"
)

# baseline 은 JSON/스키마 강제 없이, 월가 최상위 IB(Goldman Sachs GIR, Morgan Stanley Research,
# JPMorgan, BlackRock Investment Institute 급) 매크로 데스크의 시니어 애널리스트가
# 기관 투자자에게 브리핑하는 톤으로 3문장 답변을 받는다.
_BASELINE_INSTRUCTIONS = (
    "당신은 월가 최상위 IB(예: Goldman Sachs GIR, Morgan Stanley Research, JPMorgan, "
    "BlackRock Investment Institute 수준)의 글로벌 매크로·크로스에셋 전략 데스크에서 활동하는 "
    "시니어 애널리스트입니다. 기관 투자자에게 데일리 리스크 브리핑을 하듯, 정확하고 절제된 "
    "권위 있는 한국어 전문가 톤으로 답변합니다.\n"
    "\n"
    "필수 규칙:\n"
    "1) 정확히 3문장으로 구성합니다. 각 문장은 한 줄이며, 번호·불릿·마크다운·코드펜스·따옴표를 "
    "   절대 사용하지 마십시오. 문장 사이는 개행 하나로 구분합니다.\n"
    "2) 첫 번째 문장: 지금 시장이 Risk-on 인지 Risk-off 인지에 대한 결론을 단정적이되 절제된 "
    "   톤으로 제시합니다(예: '초입', '우위', '기울기' 등 정밀한 표현 권장).\n"
    "3) 두 번째 문장: 결론을 지지하는 가장 강한 드라이버 하나를 구체적 채널(유동성, 연준 정책 경로, "
    "   실질금리·장단기 스프레드, 달러지수 DXY, 신용 스프레드, 브렉이븐·기대인플레이션, VIX, "
    "   지정학 리스크, 실적 모멘텀, 외국인·기관 수급, 크로스에셋 로테이션 등)에서 기관급 용어로 "
    "   설명합니다.\n"
    "4) 세 번째 문장: 현 판단을 무효화할 수 있는 반증 시그널(invalidation) 또는 포지셔닝/리스크 "
    "   관리 시사점을 간결하게 덧붙입니다.\n"
    "5) 시장 표준 용어(VIX, DXY, 2s10s, ERP, 크레딧 스프레드, ISM, CPI, PCE, WTI, EM FX, "
    "   리스크 온·오프 로테이션 등)를 자연스럽게 섞되 과도한 나열은 금지합니다.\n"
    "6) 감정적 표현, 투자 권유 문구('매수하십시오', '사셔야 합니다' 등), 저작권 소지가 있는 "
    "   특정 인물·채널·영상·리서치 기관명을 절대 노출하지 마십시오. 출처는 '글로벌 자산군 "
    "   시그널', '최근 매크로 데이터' 등 일반화된 표현으로 대체합니다.\n"
    "7) 문장 길이는 간결하게 유지하고, 불필요한 부사와 애매모호한 관용구를 제거합니다.\n"
    "8) 모든 문장은 반드시 한국어 존댓말(격식체)로 마무리합니다. 문장 종결 어미는 "
    "   '~입니다', '~습니다', '~됩니다', '~보입니다', '~판단됩니다' 와 같이 정중한 종결 형태만 "
    "   허용되며, '~이다', '~한다', '~된다' 같은 해라체/평서문 어미는 절대 사용하지 마십시오.\n"
)

_BASELINE_QUESTION = "지금 시장이 risk on이니 off니?"

_ALIGNMENT_SUFFIX = (
    "\n\n중요(통합 정렬): 다른 분석 파이프라인이 이미 오늘 시장을 "
    "'{aligned_label}' 으로 판단하였습니다. 당신은 이 결론을 그대로 수용하여, "
    "그에 부합하는 전문가 견해를 3문장으로 서술하십시오. "
    "첫 문장은 시장이 '{aligned_label}' 쪽임을 자연스럽게 확인·부연하고, "
    "두 번째·세 번째 문장은 해당 판단을 지지하는 드라이버와 반증 시그널·포지셔닝을 "
    "기관 투자자 브리핑 톤으로 설명합니다. "
    "이 결론과 반대되는 방향(반대 극)으로 결론을 뒤집지 마십시오.\n"
)

_ALIGNMENT_LABELS = {
    RiskStatus.RISK_ON: "Risk-on",
    RiskStatus.RISK_OFF: "Risk-off",
}

_JSON_SCHEMA = {
    "type": "json_schema",
    "name": "market_risk_judgement",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "reasons"],
        "properties": {
            "status": {
                "type": "string",
                "enum": ["RISK_ON", "RISK_OFF", "UNKNOWN"],
            },
            "reasons": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string"},
            },
        },
    },
}


def _build_contextual_input(reference_date: date, note_context: str, video_context: str) -> str:
    return (
        f"[기준 일자]\n{reference_date.isoformat()}\n\n"
        f"[학습 노트]\n{note_context}\n\n"
        f"[최근 7일 참고 영상]\n{video_context}\n\n"
        "질문: 오늘 기준 한국 시장은 Risk-on 인가요, Risk-off 인가요? "
        "3줄 이내 근거와 함께 JSON 으로만 답변하십시오."
    )


class LangChainRiskJudgementAdapter(RiskJudgementLlmPort):
    """OpenAI Responses API (gpt-5-mini) 기반 Risk-on/Risk-off 판단 어댑터."""

    def __init__(self, client: OpenAIResponsesClient):
        self._client = client
        self._model = getattr(client, "_model", "gpt-5-mini")

    async def judge(
        self,
        reference_date: date,
        note_context: Optional[str] = None,
        video_context: Optional[str] = None,
        aligned_status: Optional[RiskStatus] = None,
    ) -> RiskJudgementResult:
        if note_context is None and video_context is None:
            return await self._judge_baseline(reference_date, aligned_status=aligned_status)
        return await self._judge_contextual(reference_date, note_context, video_context)

    async def _judge_contextual(
        self,
        reference_date: date,
        note_context: Optional[str],
        video_context: Optional[str],
    ) -> RiskJudgementResult:
        instructions = _CONTEXTUAL_INSTRUCTIONS.replace(
            "{reference_date}", reference_date.isoformat()
        )
        input_text = _build_contextual_input(
            reference_date,
            note_context or "(학습 노트 없음)",
            video_context or "(최근 참고 영상 없음)",
        )
        print(
            f"[macro.llm] 요청 mode=contextual model={self._model} "
            f"date={reference_date.isoformat()} input_len={len(input_text)}"
        )
        result = await self._client.create(
            instructions=instructions,
            input_text=input_text,
            text_format=_JSON_SCHEMA,
        )
        print(
            f"[macro.llm] 응답 수신 mode=contextual raw_len={len(result.output_text)} "
            f"preview={result.output_text[:200]!r}"
        )
        parsed = self._parse_contextual(result.output_text)
        print(
            f"[macro.llm] 파싱 완료 mode=contextual status={parsed.status.value} "
            f"reasons={len(parsed.reasons)}"
        )
        return parsed

    async def _judge_baseline(
        self,
        reference_date: date,
        aligned_status: Optional[RiskStatus] = None,
    ) -> RiskJudgementResult:
        instructions = _BASELINE_INSTRUCTIONS
        align_label = None
        if aligned_status in _ALIGNMENT_LABELS:
            align_label = _ALIGNMENT_LABELS[aligned_status]
            instructions = instructions + _ALIGNMENT_SUFFIX.replace(
                "{aligned_label}", align_label
            )

        print(
            f"[macro.llm] 요청 mode=baseline model={self._model} "
            f"date={reference_date.isoformat()} aligned_to={align_label or 'none'} "
            f"question={_BASELINE_QUESTION!r}"
        )
        result = await self._client.create(
            instructions=instructions,
            input_text=_BASELINE_QUESTION,
        )
        print(
            f"[macro.llm] 응답 수신 mode=baseline raw_len={len(result.output_text)} "
            f"preview={result.output_text[:200]!r}"
        )
        parsed = self._parse_baseline(result.output_text)

        # aligned_status 가 지정된 경우, 정렬 실패 방지 — status 를 강제로 지정값으로 덮는다.
        if aligned_status is not None:
            if parsed.status != aligned_status:
                print(
                    f"[macro.llm] ⚠ baseline status={parsed.status.value} "
                    f"가 aligned_status={aligned_status.value} 와 다름 → 강제 정렬"
                )
            parsed = RiskJudgementResult(status=aligned_status, reasons=parsed.reasons)

        print(
            f"[macro.llm] 파싱 완료 mode=baseline status={parsed.status.value} "
            f"reasons={len(parsed.reasons)}"
        )
        return parsed

    @staticmethod
    def _parse_contextual(raw: str) -> RiskJudgementResult:
        text = (raw or "").strip()
        if not text:
            return RiskJudgementResult(status=RiskStatus.UNKNOWN, reasons=[])

        payload = LangChainRiskJudgementAdapter._extract_json_object(text)
        if payload is None:
            print(f"[macro.llm] ⚠ contextual JSON 파싱 실패 raw={text[:200]}")
            logger.warning("[macro] contextual JSON 파싱 실패: %s", text[:300])
            return RiskJudgementResult(status=RiskStatus.UNKNOWN, reasons=[])

        status = RiskStatus.parse(str(payload.get("status", "")))
        raw_reasons = payload.get("reasons", [])
        reasons: List[str] = []
        if isinstance(raw_reasons, list):
            for item in raw_reasons:
                if item is None:
                    continue
                line = str(item).strip()
                if line:
                    reasons.append(line)
        return RiskJudgementResult(status=status, reasons=reasons[:3])

    @staticmethod
    def _parse_baseline(raw: str) -> RiskJudgementResult:
        text = (raw or "").strip()
        if not text:
            return RiskJudgementResult(status=RiskStatus.UNKNOWN, reasons=[])

        # 줄 기준 분리 → 부족하면 문장 기준 재분리
        lines = [ln.strip(" -•·\t") for ln in text.split("\n") if ln.strip()]
        if len(lines) < 2:
            sentences = re.split(r"(?<=[다요죠니까])\.\s+|(?<=[다요죠니까])\.\n|\.(?=\s|$)", text)
            lines = [s.strip() for s in sentences if s and s.strip()]

        lines = [re.sub(r"^[0-9]+[\.\)]\s*", "", ln) for ln in lines][:3]

        status = RiskStatus.UNKNOWN
        joined = text.lower()
        if "risk-off" in joined or "risk off" in joined or "리스크오프" in text or "리스크 오프" in text or "위험 회피" in text or "위험회피" in text:
            status = RiskStatus.RISK_OFF
        elif "risk-on" in joined or "risk on" in joined or "리스크온" in text or "리스크 온" in text or "위험 선호" in text or "위험선호" in text:
            status = RiskStatus.RISK_ON

        return RiskJudgementResult(status=status, reasons=lines)

    @staticmethod
    def _extract_json_object(text: str):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
