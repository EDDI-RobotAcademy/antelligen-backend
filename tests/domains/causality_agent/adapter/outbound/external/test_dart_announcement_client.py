"""DART 공시 → AnnouncementItem 변환 검증 (OKR 1 P1.5)."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.causality_agent.adapter.outbound.external.dart_announcement_client import (
    DartAnnouncementClient,
    _classify_dart_type,
    _parse_rcept_dt,
    _build_dart_url,
)
from app.domains.dashboard.domain.entity.announcement_event import AnnouncementEventType
from app.domains.disclosure.application.port.dart_disclosure_api_port import (
    DartDisclosureInfo,
)


def _make_info(report_nm: str, pblntf_ty: str = "B", rcept_no: str = "20240315000123",
               rcept_dt: str = "20240315") -> DartDisclosureInfo:
    return DartDisclosureInfo(
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_nm=report_nm,
        rcept_no=rcept_no,
        flr_nm="삼성전자",
        rcept_dt=rcept_dt,
        rm="",
        pblntf_ty=pblntf_ty,
        pblntf_detail_ty="",
    )


# ── _classify_dart_type ──────────────────────────────────────


def test_classify_earnings_guidance():
    """잠정실적 / 공정공시 + 실적 → EARNINGS_GUIDANCE."""
    assert _classify_dart_type("연결재무제표 기준 영업(잠정)실적(공정공시)", "I") == AnnouncementEventType.EARNINGS_GUIDANCE
    assert _classify_dart_type("매출액또는손익구조 30% (대규모 법인 15%) 이상 변동(자율공시)", "I") == AnnouncementEventType.MAJOR_EVENT  # 실적 키워드 없음 → fallback
    assert _classify_dart_type("잠정실적 발표", "I") == AnnouncementEventType.EARNINGS_GUIDANCE


def test_classify_earnings_release_pblntf_a():
    """pblntf_ty=A(정기) → EARNINGS_RELEASE."""
    assert _classify_dart_type("사업보고서", "A") == AnnouncementEventType.EARNINGS_RELEASE
    assert _classify_dart_type("분기보고서", "A") == AnnouncementEventType.EARNINGS_RELEASE
    assert _classify_dart_type("반기보고서", "A") == AnnouncementEventType.EARNINGS_RELEASE


def test_classify_korean_specific():
    """한국 특화 분류 — 자사주/액면분할/유무상증자."""
    assert _classify_dart_type("자기주식취득결정", "B") == AnnouncementEventType.TREASURY_STOCK
    assert _classify_dart_type("자사주 처분결정", "B") == AnnouncementEventType.TREASURY_STOCK
    assert _classify_dart_type("주식분할(액면분할)결정", "B") == AnnouncementEventType.STOCK_SPLIT
    assert _classify_dart_type("유상증자결정", "C") == AnnouncementEventType.RIGHTS_OFFERING
    assert _classify_dart_type("무상증자결정", "C") == AnnouncementEventType.BONUS_ISSUE
    assert _classify_dart_type("주식배당결정", "C") == AnnouncementEventType.BONUS_ISSUE


def test_classify_merger_acquisition():
    assert _classify_dart_type("회사합병결정", "B") == AnnouncementEventType.MERGER_ACQUISITION
    assert _classify_dart_type("타법인 주식 및 출자증권 인수결정", "B") == AnnouncementEventType.MERGER_ACQUISITION
    assert _classify_dart_type("회사분할결정", "B") == AnnouncementEventType.MERGER_ACQUISITION


def test_classify_debt_issuance():
    assert _classify_dart_type("회사채발행결정", "C") == AnnouncementEventType.DEBT_ISSUANCE
    assert _classify_dart_type("전환사채권발행결정", "C") == AnnouncementEventType.DEBT_ISSUANCE
    assert _classify_dart_type("신주인수권부사채권발행결정", "C") == AnnouncementEventType.DEBT_ISSUANCE


def test_classify_crisis():
    assert _classify_dart_type("거래정지 안내", "I") == AnnouncementEventType.CRISIS
    assert _classify_dart_type("관리종목 지정", "I") == AnnouncementEventType.CRISIS
    assert _classify_dart_type("상장폐지 결정", "I") == AnnouncementEventType.CRISIS
    assert _classify_dart_type("투자주의 환기종목 지정", "I") == AnnouncementEventType.CRISIS


def test_classify_governance():
    assert _classify_dart_type("정관 일부 변경", "B") == AnnouncementEventType.ARTICLES_AMENDMENT
    assert _classify_dart_type("정기주주총회 소집결의", "B") == AnnouncementEventType.SHAREHOLDER_MEETING
    assert _classify_dart_type("대표이사변경", "B") == AnnouncementEventType.MANAGEMENT_CHANGE
    assert _classify_dart_type("이사회 결의 결과", "B") == AnnouncementEventType.MANAGEMENT_CHANGE


def test_classify_corrections():
    assert _classify_dart_type("[기재정정] 사업보고서", "A") == AnnouncementEventType.ACCOUNTING_ISSUE


def test_classify_contract():
    assert _classify_dart_type("단일판매·공급계약체결", "B") == AnnouncementEventType.CONTRACT
    assert _classify_dart_type("대형 수주 결정", "B") == AnnouncementEventType.CONTRACT


def test_classify_fallback_major_event():
    """매칭 안 되는 공시 → MAJOR_EVENT (KR3 안전장치)."""
    assert _classify_dart_type("기타 알 수 없는 공시", "E") == AnnouncementEventType.MAJOR_EVENT
    assert _classify_dart_type("", "") == AnnouncementEventType.MAJOR_EVENT


# ── helpers ──────────────────────────────────────────────────


def test_parse_rcept_dt():
    assert _parse_rcept_dt("20240315") == date(2024, 3, 15)
    assert _parse_rcept_dt("invalid") is None
    assert _parse_rcept_dt("") is None
    assert _parse_rcept_dt(None) is None  # type: ignore[arg-type]


def test_build_dart_url():
    url = _build_dart_url("20240315000123")
    assert url == "https://dart.fss.or.kr/dsaf001/main.do?rceptNo=20240315000123"


# ── DartAnnouncementClient.fetch_announcements ──────────────


@pytest.mark.asyncio
async def test_fetch_announcements_returns_dict_list():
    """공시 dict 배열 반환 — 키 일관성 검증."""
    fake_items = [
        _make_info("자기주식 취득결정", pblntf_ty="B", rcept_no="20240315000001", rcept_dt="20240315"),
        _make_info("회사합병결정", pblntf_ty="B", rcept_no="20240320000002", rcept_dt="20240320"),
    ]
    dart_mock = MagicMock()
    dart_mock.fetch_all_pages = AsyncMock(return_value=fake_items)

    client = DartAnnouncementClient(dart_client=dart_mock)
    result = await client.fetch_announcements(
        ticker="005930.KS", corp_code="00126380",
        start_date=date(2024, 3, 1), end_date=date(2024, 3, 31),
    )

    assert len(result) == 2
    first = result[0]
    assert first["date"] == "2024-03-15"
    assert first["type"] == "TREASURY_STOCK"
    assert first["title"] == "자기주식 취득결정"
    assert first["source"] == "dart"
    assert first["url"].startswith("https://dart.fss.or.kr/dsaf001/main.do?rceptNo=")
    assert first["items_str"] is None
    assert result[1]["type"] == "MERGER_ACQUISITION"


@pytest.mark.asyncio
async def test_fetch_announcements_empty_corp_code():
    """corp_code 빈 값 → 즉시 빈 배열, DART API 호출 안 함."""
    dart_mock = MagicMock()
    dart_mock.fetch_all_pages = AsyncMock()

    client = DartAnnouncementClient(dart_client=dart_mock)
    result = await client.fetch_announcements(
        ticker="UNKNOWN", corp_code="",
        start_date=date(2024, 3, 1), end_date=date(2024, 3, 31),
    )

    assert result == []
    dart_mock.fetch_all_pages.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_announcements_dart_failure_returns_empty():
    """DART API 예외 시 raise X, 빈 배열 graceful."""
    dart_mock = MagicMock()
    dart_mock.fetch_all_pages = AsyncMock(side_effect=RuntimeError("DART down"))

    client = DartAnnouncementClient(dart_client=dart_mock)
    result = await client.fetch_announcements(
        ticker="005930.KS", corp_code="00126380",
        start_date=date(2024, 3, 1), end_date=date(2024, 3, 31),
    )

    assert result == []


@pytest.mark.asyncio
async def test_fetch_announcements_skips_invalid_dates():
    """rcept_dt 형식 깨진 항목은 skip 후 정상 항목만 반환."""
    fake_items = [
        _make_info("자기주식 취득", rcept_dt="invalid"),
        _make_info("회사합병결정", rcept_dt="20240320"),
    ]
    dart_mock = MagicMock()
    dart_mock.fetch_all_pages = AsyncMock(return_value=fake_items)

    client = DartAnnouncementClient(dart_client=dart_mock)
    result = await client.fetch_announcements(
        ticker="005930.KS", corp_code="00126380",
        start_date=date(2024, 3, 1), end_date=date(2024, 3, 31),
    )

    assert len(result) == 1
    assert result[0]["date"] == "2024-03-20"


@pytest.mark.asyncio
async def test_fetch_announcements_passes_correct_date_format():
    """start_date / end_date 가 YYYYMMDD 로 변환되어 DART API 에 전달."""
    dart_mock = MagicMock()
    dart_mock.fetch_all_pages = AsyncMock(return_value=[])

    client = DartAnnouncementClient(dart_client=dart_mock)
    await client.fetch_announcements(
        ticker="005930.KS", corp_code="00126380",
        start_date=date(2024, 1, 5), end_date=date(2024, 1, 31),
    )

    dart_mock.fetch_all_pages.assert_awaited_once()
    kwargs = dart_mock.fetch_all_pages.await_args.kwargs
    assert kwargs["bgn_de"] == "20240105"
    assert kwargs["end_de"] == "20240131"
    assert kwargs["corp_code"] == "00126380"
