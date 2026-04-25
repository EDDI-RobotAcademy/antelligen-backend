import io
import logging
import re
import zipfile
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.domains.disclosure.application.port.dart_document_api_port import DartDocumentApiPort
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


class DartDocumentApiClient(DartDocumentApiPort):

    async def fetch_document(self, rcept_no: str) -> str:
        """DART에서 공시 원문 ZIP을 다운로드하여 텍스트를 추출한다."""
        settings = get_settings()

        params = {
            "crtfc_key": settings.open_dart_api_key,
            "rcept_no": rcept_no,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(DART_DOCUMENT_URL, params=params)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        # DART API가 에러를 XML로 반환하는 경우 처리
        if "application/xml" in content_type or "text/xml" in content_type:
            error_text = response.text
            # status=014 ("파일이 존재하지 않습니다") 는 DART에서 삭제·이관된 공시에 대한
            # 정상 응답이므로 INFO 로 격하한다.
            if "<status>014</status>" in error_text:
                logger.info("DART 문서 없음(삭제/이관): rcept_no=%s", rcept_no)
            else:
                logger.error("DART 문서 API 오류 응답: rcept_no=%s, response=%s", rcept_no, error_text)
            raise RuntimeError(f"DART 문서 API 오류: {error_text}")

        # ZIP 파일에서 텍스트 추출
        raw_text = self._extract_text_from_zip(response.content, rcept_no)

        if not raw_text or not raw_text.strip():
            logger.warning("DART 문서에서 텍스트를 추출하지 못했습니다: rcept_no=%s", rcept_no)
            raise RuntimeError(f"DART 문서 텍스트 추출 실패: rcept_no={rcept_no}")

        logger.info(
            "DART 문서 원문 추출 완료: rcept_no=%s, length=%d",
            rcept_no,
            len(raw_text),
        )
        return raw_text

    def _extract_text_from_zip(self, zip_bytes: bytes, rcept_no: str) -> str:
        """ZIP 바이트에서 XML/HTML 파일을 추출하여 텍스트를 반환한다."""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                file_names = zf.namelist()

                if not file_names:
                    logger.warning("ZIP 파일이 비어있습니다: rcept_no=%s", rcept_no)
                    return ""

                # 주요 문서 파일 선택 (XML 또는 HTML 우선)
                target_file = self._select_main_document(file_names)
                if target_file is None:
                    logger.warning(
                        "ZIP에서 문서 파일을 찾지 못했습니다: rcept_no=%s, files=%s",
                        rcept_no,
                        file_names,
                    )
                    return ""

                raw_bytes = zf.read(target_file)
                raw_content = self._decode_bytes(raw_bytes)
                return self._clean_html_to_text(raw_content)

        except zipfile.BadZipFile:
            logger.error("유효하지 않은 ZIP 파일입니다: rcept_no=%s", rcept_no)
            raise RuntimeError(f"유효하지 않은 ZIP 파일: rcept_no={rcept_no}")

    @staticmethod
    def _select_main_document(file_names: list[str]) -> Optional[str]:
        """ZIP 내 파일 목록에서 주요 문서 파일을 선택한다."""
        # XML 파일 우선
        xml_files = [f for f in file_names if f.lower().endswith(".xml")]
        if xml_files:
            return xml_files[0]

        # HTML 파일
        html_files = [
            f for f in file_names if f.lower().endswith((".html", ".htm"))
        ]
        if html_files:
            return html_files[0]

        # 그 외 첫 번째 파일
        return file_names[0] if file_names else None

    @staticmethod
    def _decode_bytes(raw_bytes: bytes) -> str:
        """바이트를 문자열로 디코딩한다 (UTF-8 우선, EUC-KR 폴백)."""
        for encoding in ("utf-8", "euc-kr", "cp949"):
            try:
                return raw_bytes.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw_bytes.decode("utf-8", errors="replace")

    @staticmethod
    def _clean_html_to_text(html_content: str) -> str:
        """HTML/XML 콘텐츠에서 태그를 제거하고 텍스트를 추출한다."""
        soup = BeautifulSoup(html_content, "html.parser")

        # script, style 태그 제거
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n")

        # 연속 공백/빈줄 정리
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        cleaned = "\n".join(lines)

        # 과도한 공백 제거
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        return cleaned
