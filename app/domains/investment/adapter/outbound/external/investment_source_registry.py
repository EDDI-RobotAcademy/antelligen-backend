"""
투자 워크플로우 데이터 소스 레지스트리.

SOURCE_REGISTRY 에 등록된 키만 실제 구현된 소스로 인정한다.
- Query Parser 는 이 키 목록을 보고 LLM 프롬프트를 구성한다.
- Retrieval Agent 는 이 키만 통과시키고 나머지는 무시한다.
- 향후 소스를 추가할 때 이 파일에만 등록하면 나머지가 자동 연동된다.
"""

# 구현된 소스 레지스트리: {소스명: 설명}
SOURCE_REGISTRY: dict[str, str] = {
    "뉴스": "SERP API Google News — 최신 뉴스 기사",
    "유튜브": "YouTube Data API v3 — 투자 관련 영상 및 댓글",
    # 확장 포인트 (미구현):
    # "종목": "종목 시세 및 기본 정보",
    # "재무데이터": "DART 재무제표 데이터",
    # "시장데이터": "시장 지수 및 섹터 데이터",
    # "공시정보": "DART 공시 정보",
}

# 구현된 소스 키 집합 (O(1) 조회용)
IMPLEMENTED_SOURCE_KEYS: frozenset[str] = frozenset(SOURCE_REGISTRY.keys())

# LLM 파싱 실패 / 미구현 소스만 반환 시 사용하는 기본 소스
DEFAULT_SOURCES: list[str] = list(SOURCE_REGISTRY.keys())
