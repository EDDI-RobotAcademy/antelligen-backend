import logging
from datetime import datetime

from app.domains.disclosure.application.port.dart_document_api_port import DartDocumentApiPort
from app.domains.disclosure.application.port.disclosure_document_repository_port import (
    DisclosureDocumentRepositoryPort,
)
from app.domains.disclosure.application.port.disclosure_repository_port import (
    DisclosureRepositoryPort,
)
from app.domains.disclosure.application.port.embedding_port import EmbeddingPort
from app.domains.disclosure.application.port.rag_chunk_repository_port import (
    RagChunkRepositoryPort,
)
from app.domains.disclosure.domain.entity.disclosure_document import DisclosureDocument
from app.domains.disclosure.domain.entity.rag_document_chunk import RagDocumentChunk
from app.domains.disclosure.domain.service.disclosure_document_parser import (
    DisclosureDocumentParser,
)
from app.domains.disclosure.domain.service.text_chunker import TextChunker

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 200


class ProcessDisclosureDocumentsUseCase:
    """공시 원문을 DART에서 가져와 요약 + RAG 청크를 한 번에 처리한다.

    원문(raw_text)은 DB에 저장하지 않고 메모리에서 즉시 가공한 뒤
    요약문(summary_text)과 RAG 청크(embedding)만 저장한다.
    """

    def __init__(
        self,
        dart_document_api: DartDocumentApiPort,
        disclosure_document_repository: DisclosureDocumentRepositoryPort,
        disclosure_repository: DisclosureRepositoryPort,
        rag_chunk_repository: RagChunkRepositoryPort,
        embedding_port: EmbeddingPort,
    ):
        self._dart_doc_api = dart_document_api
        self._doc_repo = disclosure_document_repository
        self._disclosure_repo = disclosure_repository
        self._rag_repo = rag_chunk_repository
        self._embedding = embedding_port
        self._parser = DisclosureDocumentParser()
        self._chunker = TextChunker()

    async def execute(self, limit: int = 50) -> dict:
        """미처리 공시 문서를 일괄 처리한다.

        Returns:
            처리 결과 요약 dict
        """
        # 1. 아직 처리되지 않은 핵심 공시 조회
        disclosures = await self._disclosure_repo.find_unprocessed_core(limit=limit)

        if not disclosures:
            logger.info("[문서처리] 처리 대상 없음")
            return {"processed": 0, "chunks_stored": 0, "failed": 0, "message": "처리 대상 없음"}

        processed = 0
        chunks_stored = 0
        failed = 0

        for disclosure in disclosures:
            try:
                result = await self._process_single(disclosure)
                processed += 1
                chunks_stored += result
                logger.info(
                    "[문서처리] 완료: rcept_no=%s, %s, 청크 %d건",
                    disclosure.rcept_no, disclosure.report_nm, result,
                )
            except Exception as e:
                failed += 1
                # DART status=014 (파일 없음) 은 삭제·이관된 공시라 영구 실패가 정상 — INFO 로 격하한다.
                if "<status>014</status>" in str(e):
                    logger.info(
                        "[문서처리] 스킵(파일 없음): rcept_no=%s",
                        disclosure.rcept_no,
                    )
                else:
                    logger.error(
                        "[문서처리] 실패: rcept_no=%s, %s",
                        disclosure.rcept_no, e,
                    )

        message = f"문서 처리 완료: {processed}건 성공, {failed}건 실패, 청크 {chunks_stored}건 저장"
        logger.info("[문서처리] %s", message)
        return {"processed": processed, "chunks_stored": chunks_stored, "failed": failed, "message": message}

    async def _process_single(self, disclosure) -> int:
        """단일 공시를 처리한다. 반환값은 저장된 청크 수."""
        rcept_no = disclosure.rcept_no

        # 1. DART에서 원문 다운로드 (메모리에만 보관)
        raw_text = await self._dart_doc_api.fetch_document(rcept_no)

        # 2. 파싱 + 요약 생성
        parsed_json = self._parser.parse(raw_text)
        summary_text = self._parser.generate_summary(raw_text)

        # 3. disclosure_documents에 요약만 저장 (raw_text=None)
        doc = DisclosureDocument(
            rcept_no=rcept_no,
            document_type=self._classify_document_type(disclosure),
            raw_text=None,
            parsed_json=parsed_json,
            summary_text=summary_text,
            stored_in_rag=True,
            collected_at=datetime.now(),
        )
        saved_doc = await self._doc_repo.upsert(doc)

        # 4. RAG 청크 생성 + 임베딩 + 저장
        chunks_count = 0
        if raw_text and len(raw_text) >= MIN_TEXT_LENGTH:
            chunk_dicts = self._chunker.chunk_text(raw_text)
            if chunk_dicts:
                chunk_texts = [c["chunk_text"] for c in chunk_dicts]
                embeddings = await self._embedding.generate_batch(chunk_texts)

                chunks = [
                    RagDocumentChunk(
                        rcept_no=rcept_no,
                        corp_code=disclosure.corp_code,
                        disclosure_document_id=saved_doc.document_id,
                        report_nm=disclosure.report_nm,
                        document_type=doc.document_type,
                        section_title=cd["section_title"],
                        chunk_index=cd["chunk_index"],
                        chunk_text=cd["chunk_text"],
                        chunk_hash=cd["chunk_hash"],
                        embedding=emb,
                    )
                    for cd, emb in zip(chunk_dicts, embeddings)
                ]

                chunks_count = await self._rag_repo.upsert_bulk(chunks)

        return chunks_count

    @staticmethod
    def _classify_document_type(disclosure) -> str:
        """공시 유형에 따라 document_type을 결정한다."""
        group = disclosure.disclosure_group
        if group == "report":
            return "report_document"
        elif group == "event":
            return "event_document"
        return "core_document"
