"""방산 도메인 동의어 매핑 테이블.

각 항목은 {대표 키워드: {동의어 집합}} 형태로 정의한다.
동의어들은 추출 후 대표 키워드로 통합된다.
"""

from typing import FrozenSet

# 대표 키워드 → 동의어 집합 (대표 키워드 자체도 포함)
DEFENSE_SYNONYM_GROUPS: dict[str, FrozenSet[str]] = {
    # 방산 / 방위산업 관련
    "방산주": frozenset({"방산주", "방산株", "방산관련주", "방산 관련주", "방위산업주", "방위산업 관련주"}),
    "방위산업": frozenset({"방위산업", "방산업", "방산", "방위산업체"}),
    "방산수출": frozenset({"방산수출", "방위산업수출", "K방산수출", "방산 수출"}),

    # 주요 방산 기업
    "한화에어로스페이스": frozenset({"한화에어로스페이스", "한화에어로", "한화aerospace", "한화Aerospace"}),
    "현대로템": frozenset({"현대로템", "현대 로템", "로템"}),
    "LIG넥스원": frozenset({"LIG넥스원", "LIG넥스", "LIG Nex1", "넥스원"}),
    "한국항공우주": frozenset({"한국항공우주", "KAI", "항공우주산업"}),
    "풍산": frozenset({"풍산", "풍산그룹"}),
    "한화시스템": frozenset({"한화시스템", "한화 시스템"}),

    # 무기 체계
    "K2전차": frozenset({"K2전차", "K2 전차", "흑표전차", "흑표"}),
    "K9자주포": frozenset({"K9자주포", "K9 자주포", "K9", "천무"}),
    "FA50": frozenset({"FA50", "FA-50", "경공격기"}),

    # 지수 / 시장
    "코스피": frozenset({"코스피", "KOSPI", "코스피지수"}),
    "코스닥": frozenset({"코스닥", "KOSDAQ", "코스닥지수"}),

    # 국제 정세
    "우크라이나": frozenset({"우크라이나", "우크라", "Ukraine"}),
    "러시아": frozenset({"러시아", "Russia", "러시"}),
    "나토": frozenset({"나토", "NATO", "북대서양조약기구"}),

    # 주식 관련 일반 용어
    "주가": frozenset({"주가", "주식가격", "시세"}),
    "상승": frozenset({"상승", "급등", "강세", "오름"}),
    "하락": frozenset({"하락", "급락", "약세", "내림"}),
}

# 역방향 매핑: 동의어 → 대표 키워드 (빠른 조회용)
SYNONYM_TO_CANONICAL: dict[str, str] = {
    variant: canonical
    for canonical, variants in DEFENSE_SYNONYM_GROUPS.items()
    for variant in variants
}
