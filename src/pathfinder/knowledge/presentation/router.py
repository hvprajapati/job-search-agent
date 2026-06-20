"""Knowledge API routes."""
import io
import logging
import re
from uuid import UUID
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
import PyPDF2
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.knowledge.domain.entities import KnowledgeDocument
from pathfinder.knowledge.domain.value_objects import KnowledgeSource, RetrievalQuery
from pathfinder.knowledge.infrastructure.ingestion.pipeline import IngestionPipeline
from pathfinder.knowledge.infrastructure.persistence.repositories import (
    SqlKnowledgeDocumentRepository, SqlKnowledgeChunkRepository,
)
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge"])


def _extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from uploaded file, handling PDFs with PyPDF2."""
    lower = filename.lower()

    if lower.endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            pages: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            text = "\n\n".join(pages)
            if text.strip():
                logger.info("Extracted %d chars from %d PDF pages", len(text), len(reader.pages))
                return text
        except Exception as exc:
            logger.warning("PyPDF2 extraction failed for %s: %s", filename, exc)

    # Fallback: try UTF-8 decode (for .txt, .md, .docx plain text)
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    return text


def _sanitize_text(text: str) -> str:
    """Remove null bytes and control characters that PostgreSQL rejects."""
    # Remove null bytes (0x00) — rejected by PostgreSQL UTF8
    text = text.replace("\x00", "")
    # Remove other problematic control chars but keep newlines and tabs
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    return text


@router.post("/ingest/document")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Query("Uploaded Document"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    file_bytes = await file.read()
    filename = file.filename or "untitled"

    text = _extract_text(file_bytes, filename)
    text = _sanitize_text(text)

    if not text or len(text.strip()) < 50:
        from pathfinder.shared.domain.exceptions import ValidationError
        detail = "Could not extract meaningful text from file. For PDFs, ensure the document contains selectable text (not scanned images)."
        raise ValidationError(detail, field="file")

    doc = KnowledgeDocument.from_text(
        user_id=current_user.id, source_type=KnowledgeSource.USER_UPLOAD,
        source_id="", title=title, content=text,
    )
    pipeline = IngestionPipeline()
    chunk_count = await pipeline.ingest(doc)
    return {"data": {"chunks_created": chunk_count, "title": title}}


@router.post("/search")
async def search_knowledge(
    query: str = Query(...),
    top_k: int = Query(5, le=20),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlKnowledgeChunkRepository(session)
    embedder = DeepSeekClient()
    q_embedding = await embedder.generate_embedding(query)
    rq = RetrievalQuery(query_text=query, user_id=str(current_user.id), top_k=top_k)
    results = await repo.hybrid_search(query=rq, query_embedding=q_embedding)
    return {
        "data": [
            {"chunk_id": r.chunk_id, "content": r.content[:300],
             "score": r.score, "source": r.metadata.source_name if r.metadata else "",
             "excerpt": r.source_excerpt}
            for r in results
        ],
    }


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlKnowledgeDocumentRepository(session)
    docs = await repo.list_by_user(current_user.id)
    return {
        "data": [
            {"document_id": str(d.id), "title": d.title,
             "source_type": d.source_type.value, "chunk_count": d.chunk_count,
             "is_indexed": d.is_indexed}
            for d in docs
        ],
    }


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    chunk_repo = SqlKnowledgeChunkRepository(session)
    await chunk_repo.delete_by_document(document_id)
    await session.commit()
    return Response(status_code=204)
