"""E2E Journey 6: Knowledge Ingestion & Retrieval."""
import pytest
import io


class TestKnowledgeJourney:
    async def test_ingest_text_document(self, client, auth_headers):
        text = "Python is a programming language. FastAPI is a web framework. PostgreSQL is a database."
        files = {"file": ("doc.txt", io.BytesIO(text.encode()), "text/plain")}
        resp = await client.post(
            "/v1/knowledge/ingest/document",
            files=files, data={"title": "Test Document"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["chunks_created"] >= 1
        assert data["title"] == "Test Document"

    async def test_search_knowledge_returns_results(self, client, auth_headers):
        resp = await client.post(
            "/v1/knowledge/search",
            params={"query": "Python", "top_k": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_list_documents(self, client, auth_headers):
        resp = await client.get("/v1/knowledge/documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)

    async def test_delete_document(self, client, auth_headers):
        # Ingest first
        text = "Temporary document for deletion test."
        files = {"file": ("temp.txt", io.BytesIO(text.encode()), "text/plain")}
        ingest_resp = await client.post(
            "/v1/knowledge/ingest/document",
            files=files, data={"title": "Temp Doc"},
            headers=auth_headers,
        )
        assert ingest_resp.status_code == 200

        docs_resp = await client.get("/v1/knowledge/documents", headers=auth_headers)
        docs = docs_resp.json()["data"]
        if docs:
            doc_id = docs[0]["document_id"]
            resp = await client.delete(
                f"/v1/knowledge/documents/{doc_id}",
                headers=auth_headers,
            )
            assert resp.status_code == 204

    async def test_reject_empty_document(self, client, auth_headers):
        files = {"file": ("empty.txt", io.BytesIO(b"ab"), "text/plain")}
        resp = await client.post(
            "/v1/knowledge/ingest/document",
            files=files, data={"title": "Too Short"},
            headers=auth_headers,
        )
        assert resp.status_code in (400, 422)

    async def test_search_requires_auth(self, client):
        resp = await client.post(
            "/v1/knowledge/search",
            params={"query": "test"},
        )
        assert resp.status_code == 401
