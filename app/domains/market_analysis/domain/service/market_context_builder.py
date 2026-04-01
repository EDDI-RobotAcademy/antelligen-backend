from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock


class MarketContextBuilder:
    """방산 종목 데이터를 LLM 프롬프트용 컨텍스트 문자열로 변환하는 도메인 서비스."""

    @staticmethod
    def build(stocks: list[DefenseStock]) -> str:
        if not stocks:
            return "[방산 종목 데이터 없음]"

        lines = ["[방산 종목 데이터]"]
        for stock in stocks:
            themes = ", ".join(stock.themes) if stock.themes else "없음"
            lines.append(f"- {stock.name} (종목코드: {stock.code}) | 관련 테마: {themes}")
        return "\n".join(lines)
