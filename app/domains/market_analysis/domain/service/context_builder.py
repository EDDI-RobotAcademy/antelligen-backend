from dataclasses import dataclass
from typing import List


@dataclass
class KeywordItem:
    keyword: str
    count: int


@dataclass
class StockThemeItem:
    name: str
    code: str
    themes: List[str]


class ContextBuilder:
    @staticmethod
    def build(keywords: List[KeywordItem], stock_themes: List[StockThemeItem]) -> str:
        lines = ["=== 최근 방산 키워드 동향 ==="]
        if keywords:
            for kw in keywords[:20]:
                lines.append(f"- {kw.keyword}: {kw.count}회 언급")
        else:
            lines.append("(키워드 데이터 없음)")

        lines.append("")
        lines.append("=== 방산 종목/테마 데이터 ===")
        if stock_themes:
            for st in stock_themes:
                themes_str = ", ".join(st.themes) if st.themes else "없음"
                lines.append(f"- {st.name} ({st.code}): {themes_str}")
        else:
            lines.append("(종목 데이터 없음)")

        return "\n".join(lines)
