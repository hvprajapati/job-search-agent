"""Integration tests for Tailoring API."""
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
async def client_and_token():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/v1/auth/register", json={
            "email": "tailor-test@test.com", "password": "Test1234!",
            "full_name": "Tailor Tester", "accept_terms": True,
        })
        token = resp.json()["data"]["tokens"]["access_token"]
        yield c, token


async def test_analyze_resume_missing_resume_returns_404(client_and_token):
    client, token = client_and_token
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/v1/tailoring/analyze",
        params={"base_resume_id": "00000000-0000-0000-0000-000000000001",
                "job_id": "00000000-0000-0000-0000-000000000002"},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_tailor_resume_requires_auth():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/v1/tailoring/tailor", params={
            "base_resume_id": "00000000-0000-0000-0000-000000000001",
            "job_id": "00000000-0000-0000-0000-000000000002",
        })
        assert resp.status_code == 401


async def test_versions_endpoint_requires_auth():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/v1/tailoring/versions", params={
            "base_resume_id": "00000000-0000-0000-0000-000000000001",
            "job_id": "00000000-0000-0000-0000-000000000002",
        })
        assert resp.status_code == 401


async def test_invalid_strategy_returns_422(client_and_token):
    client, token = client_and_token
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/v1/tailoring/tailor",
        params={
            "base_resume_id": "00000000-0000-0000-0000-000000000001",
            "job_id": "00000000-0000-0000-0000-000000000002",
            "strategy": "invalid_strategy",
        },
        headers=headers,
    )
    assert resp.status_code == 422
