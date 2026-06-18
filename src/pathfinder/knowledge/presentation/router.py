"""Knowledge API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
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

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge"])


@router.post("/ingest/document")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Query("Uploaded Document"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    file_bytes = await file.read()
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    if not text or len(text.strip()) < 50:
        from pathfinder.shared.domain.exceptions import ValidationError
        raise ValidationError("Could not extract meaningful text from file", field="file")

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
