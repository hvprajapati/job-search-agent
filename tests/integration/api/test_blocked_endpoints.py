"""Integration tests for previously-blocked endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
async def app():
    """Skip if no PostgreSQL available."""
    import os
    try:
        import asyncpg
        conn = await asyncpg.connect(os.environ.get("TEST_DATABASE_URL",
            "postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder_test"), timeout=3)
        await conn.close()
    except Exception:
        pytest.skip("PostgreSQL not available")
    return create_app()


@pytest.fixture
async def client_and_token():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/v1/auth/register", json={
            "email": "blocked-test@test.com", "password": "Test1234!",
            "full_name": "Blocked Tester", "accept_terms": True,
        })
        token = resp.json()["data"]["tokens"]["access_token"]
        yield c, token


class TestAgentExecutions:
    async def test_list_executions_returns_200(self, client_and_token):
        client, token = client_and_token
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/v1/agent/executions", headers=headers)
        assert resp.status_code == 200
        assert "data" in resp.json()
        assert "meta" in resp.json()

    async def test_list_executions_requires_auth(self, client_and_token):
        client, _ = client_and_token
        resp = await client.get("/v1/agent/executions")
        assert resp.status_code == 401

    async def test_get_execution_not_found_returns_404(self, client_and_token):
        client, token = client_and_token
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "/v1/agent/executions/00000000-0000-0000-0000-000000000001",
            headers=headers,
        )
        assert resp.status_code == 404


class TestMatchFeedback:
    async def test_record_feedback_returns_200(self, client_and_token):
        client, token = client_and_token
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/v1/match/feedback",
            params={"job_id": "00000000-0000-0000-0000-000000000001",
                    "feedback": "thumbs_up"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "feedback_recorded"

    async def test_invalid_feedback_rejected(self, client_and_token):
        client, token = client_and_token
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/v1/match/feedback",
            params={"job_id": "00000000-0000-0000-0000-000000000001",
                    "feedback": "invalid"},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_feedback_requires_auth(self, client_and_token):
        client, _ = client_and_token
        resp = await client.post(
            "/v1/match/feedback",
            params={"job_id": "00000000-0000-0000-0000-000000000001",
                    "feedback": "thumbs_up"},
        )
        assert resp.status_code == 401


class TestAuthLogout:
    async def test_logout_returns_204(self, client_and_token):
        client, token = client_and_token
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post("/v1/auth/logout", headers=headers)
        assert resp.status_code == 204

    async def test_logout_without_token_returns_401(self, client_and_token):
        client, _ = client_and_token
        resp = await client.post("/v1/auth/logout")
        assert resp.status_code == 401
