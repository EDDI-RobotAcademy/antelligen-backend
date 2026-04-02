"""공시 분석을 위한 LLM 프롬프트 빌더 (순수 Python 도메인 서비스)"""


class AnalysisPromptBuilder:

    @staticmethod
    def _format_disclosures(disclosures: list, summary_map: dict = None) -> str:
        """공시 목록을 포맷팅한다. 핵심 공시는 요약 포함, 기타 공시는 카테고리별 건수 요약."""
        if not disclosures:
            return "공시 데이터가 없습니다."

        from app.domains.disclosure.domain.service.disclosure_classifier import DisclosureClassifier

        summary_map = summary_map or {}
        core_lines = []
        other_counts: dict[str, int] = {}

        _TYPE_LABELS = {
            "earnings": "실적 관련",
            "dividend": "배당 관련",
            "fundraising": "자금조달 관련",
            "ownership": "임원ㆍ주요주주 소유 보고",
            "major_event": "주요사항",
            "unknown": "기타",
        }

        for d in disclosures:
            rcept_no = d.rcept_no if hasattr(d, "rcept_no") else ""
            rcept_dt = str(d.rcept_dt) if hasattr(d, "rcept_dt") else "N/A"
            report_nm = d.report_nm if hasattr(d, "report_nm") else "N/A"
            group = d.disclosure_group if hasattr(d, "disclosure_group") else "N/A"
            is_core = d.is_core if hasattr(d, "is_core") else False

            if is_core:
                line = f"- [{rcept_dt}] {report_nm} (분류: {group})"
                summary = summary_map.get(rcept_no)
                if summary:
                    line += f"\n  요약: {summary}"
                core_lines.append(line)
            else:
                event_type = DisclosureClassifier.classify_event_type(report_nm)
                label = _TYPE_LABELS.get(event_type, "기타")
                other_counts[label] = other_counts.get(label, 0) + 1

        parts = []
        if core_lines:
            parts.append(
                f"### 핵심 공시 ({len(core_lines)}건 / 전체 {len(disclosures)}건)\n"
                + "\n".join(core_lines)
            )
        if other_counts:
            count_lines = [f"- {label}: {count}건" for label, count in other_counts.items()]
            parts.append("### 기타 공시 현황\n" + "\n".join(count_lines))
        return "\n\n".join(parts)

    @staticmethod
    def _format_rag_contexts(rag_contexts: list) -> str:
        """RAG 검색 결과를 텍스트로 포맷팅한다."""
        if not rag_contexts:
            return "추가 근거 자료가 없습니다."

        lines = []
        for i, ctx in enumerate(rag_contexts, 1):
            report_nm = ctx.report_nm if hasattr(ctx, "report_nm") else "N/A"
            section = ctx.section_title if hasattr(ctx, "section_title") else "N/A"
            text = ctx.chunk_text if hasattr(ctx, "chunk_text") else ""
            lines.append(f"[근거 {i}] {report_nm} - {section}\n{text}")
        return "\n\n".join(lines)

    @classmethod
    def build_flow_analysis_prompt(
        cls, disclosures: list, rag_contexts: list, summary_map: dict = None,
    ) -> tuple:
        """공시 흐름 시계열 분석 프롬프트를 생성한다.

        Returns:
            tuple[str, str]: (사용자 프롬프트, 시스템 메시지)
        """
        disclosure_text = cls._format_disclosures(disclosures, summary_map)
        rag_text = cls._format_rag_contexts(rag_contexts)

        system_message = (
            "당신은 한국 주식 시장의 공시 흐름 분석 전문가입니다. "
            "공시 데이터를 시계열로 분석하되, 구체적인 날짜와 수치를 기반으로 분석합니다. "
            "RAG 참고 자료가 있으면 반드시 구체적 내용을 인용하세요. "
            "significance는 투자 영향도 기준으로 판단하세요 (자금조달·실적·배당=high, 인사·소유=medium, 단순공시=low). "
            "추상적 표현 대신 날짜·금액·비율 등 검증 가능한 사실만 사용하세요. "
            "반드시 한국어로 답변하고, JSON 형식으로만 출력하세요."
        )

        prompt = f"""다음 기업의 공시 목록을 시계열로 분석하여 주요 흐름과 변화를 파악해주세요.

## 공시 목록
{disclosure_text}

## 참고 자료 (RAG 검색 결과)
{rag_text}

## 출력 형식 (JSON)
다음 JSON 형식으로 출력해주세요:
{{
    "timeline_summary": "시계열 흐름 요약",
    "key_events": [
        {{
            "date": "날짜",
            "event": "이벤트 설명",
            "significance": "중요도 (high/medium/low)",
            "detail": "상세 분석"
        }}
    ],
    "trend_analysis": "전체적인 트렌드 분석",
    "risk_factors": ["위험 요소 1", "위험 요소 2"],
    "positive_signals": ["긍정 신호 1", "긍정 신호 2"]
}}"""

        return prompt, system_message

    @classmethod
    def build_signal_analysis_prompt(
        cls, disclosures: list, rag_contexts: list, summary_map: dict = None,
    ) -> tuple:
        """공시 기반 투자 신호 분석 프롬프트를 생성한다.

        Returns:
            tuple[str, str]: (사용자 프롬프트, 시스템 메시지)
        """
        disclosure_text = cls._format_disclosures(disclosures, summary_map)
        rag_text = cls._format_rag_contexts(rag_contexts)

        system_message = (
            "당신은 한국 주식 공시 기반 투자 신호 분석 전문가입니다. "
            "공시 데이터와 RAG 참고 자료의 구체적 수치를 인용하여 투자 신호를 도출하세요. "
            "추상적 표현 대신 날짜, 금액, 비율 등 검증 가능한 사실만 사용하세요. "
            "신호 판단 기준: 자금조달·실적 개선·배당 확대=bullish, 손실·소송·주요주주 매도=bearish, 단순 공시·혼재=neutral. "
            "confidence는 근거 수와 명확성 기준으로 결정하세요 (근거 3건↑+명확=0.7↑, 근거 부족=0.4~0.6). "
            "반드시 한국어로 답변하고, JSON 형식으로만 출력하세요."
        )

        prompt = f"""다음 기업의 공시 데이터를 분석하여 투자 신호를 도출해주세요.
RAG 참고 자료에서 확인된 수치와 사실만 사용하고, 근거 없는 추측은 하지 마세요.

## 공시 목록
{disclosure_text}

## RAG 참고 자료 (원문 발췌)
{rag_text}

## 출력 형식 (JSON)
{{
    "overall_signal": "bullish/bearish/neutral",
    "confidence": 0.0~1.0,
    "signals": [
        {{
            "type": "earnings/dividend/fundraising/ownership/major_event",
            "direction": "positive/negative/neutral",
            "strength": "strong/moderate/weak",
            "description": "구체적 근거 포함 설명 (수치/날짜 인용)",
            "based_on": "근거 공시명"
        }}
    ],
    "investment_summary": "수치 기반 투자 관점 요약",
    "cautions": ["구체적 유의사항 1", "구체적 유의사항 2"]
}}"""

        return prompt, system_message

    @classmethod
    def build_full_analysis_prompt(
        cls, disclosures: list, rag_contexts: list, summary_map: dict = None,
    ) -> tuple:
        """종합 공시 분석 프롬프트를 생성한다.

        Returns:
            tuple[str, str]: (사용자 프롬프트, 시스템 메시지)
        """
        disclosure_text = cls._format_disclosures(disclosures, summary_map)
        rag_text = cls._format_rag_contexts(rag_contexts)

        system_message = (
            "당신은 한국 주식 공시 전문 분석가입니다. "
            "제공된 공시 목록과 RAG 참고 자료(사업보고서 발췌)를 바탕으로 분석하세요. "
            "RAG 자료는 재무제표 숫자가 아닌 사업 현황, 위험 요소, 전략적 내용을 담고 있을 수 있습니다. "
            "수치가 없더라도 사업 내용과 공시 이벤트 기반으로 투자 신호를 도출할 수 있습니다. "
            "'안정적인 재무 구조', '투명한 지배구조' 같은 근거 없는 추상적 표현은 절대 사용하지 마세요. "
            "신호 판단 기준: 자금조달·실적 개선·사업 확장=bullish, 손실·소송·규제 리스크=bearish, 혼재·단순 공시=neutral. "
            "confidence 기준: 핵심 공시 3건↑ + RAG 근거 있음=0.7↑, 공시 적거나 RAG 없음=0.4~0.6, 공시 없음=0.3↓. "
            "확인된 사실과 공시 내용만 기술하고, 반드시 한국어로 JSON 형식으로만 출력하세요."
        )

        prompt = f"""다음 기업의 공시 데이터를 분석하세요. RAG 참고 자료에 구체적인 수치나 내용이 있으면 반드시 인용하세요.

## 공시 목록
{disclosure_text}

## RAG 참고 자료 (사업보고서 등 원문 발췌)
{rag_text}

## 분석 지침
- key_events: 실제 공시된 날짜와 내용을 기반으로 작성 (예: "2026-03-10 사업보고서 제출")
- signals: 공시 목록과 RAG 자료에서 확인된 사실 기반으로 작성 (사업 전략, 위험 요소, 주요 이벤트 등)
- risk_factors: 공시 및 사업보고서 내용에서 파악한 실제 리스크 기술 (규제, 경쟁, 시장 위험 등)
- positive_signals: 공시 및 사업보고서 내용에서 파악한 긍정 요인 기술 (사업 확장, 신규 투자, 성장 동력 등)
- RAG 자료에 재무 수치가 없더라도 사업 내용, 위험 요소, 전략 정보가 있으면 confidence 0.6 이상 가능
- investment_summary: 공시 이벤트와 사업 현황을 종합한 투자 관점 요약

## 출력 형식 (JSON)
{{
    "company_overview": "공시 기반 기업 현황 (구체적 수치 포함)",
    "key_events": [
        {{
            "date": "날짜",
            "event": "구체적 이벤트 (수치 포함)",
            "significance": "high/medium/low",
            "detail": "RAG 자료 인용 포함 상세 분석"
        }}
    ],
    "overall_signal": "bullish/bearish/neutral",
    "confidence": 0.0~1.0,
    "signals": [
        {{
            "type": "신호 유형",
            "direction": "positive/negative/neutral",
            "strength": "strong/moderate/weak",
            "description": "근거 공시 및 수치 포함 설명"
        }}
    ],
    "risk_factors": ["구체적 리스크 1 (수치/날짜 포함)", "구체적 리스크 2"],
    "positive_signals": ["구체적 긍정 요인 1 (수치/날짜 포함)", "구체적 긍정 요인 2"],
    "investment_summary": "수치 기반 투자 관점 종합 요약 (2~3문장)"
}}"""

        return prompt, system_message
