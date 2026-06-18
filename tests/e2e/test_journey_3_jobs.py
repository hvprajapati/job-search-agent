"""E2E Journey 3: Job Search & Discovery."""
import pytest


class TestJobSearchJourney:
    async def test_search_jobs_returns_results(self, client, auth_headers):
        resp = await client.get("/v1/jobs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data
        assert "count" in data["meta"]

    async def test_search_jobs_with_query(self, client, auth_headers):
        resp = await client.get("/v1/jobs?q=python", headers=auth_headers)
        assert resp.status_code == 200

    async def test_search_jobs_with_filters(self, client, auth_headers):
        resp = await client.get(
            "/v1/jobs?remote_policy=remote&seniority=senior&limit=5",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_get_job_not_found(self, client, auth_headers):
        resp = await client.get(
            "/v1/jobs/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_search_companies(self, client, auth_headers):
        resp = await client.get("/v1/companies?q=stripe", headers=auth_headers)
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_get_company_not_found(self, client, auth_headers):
        resp = await client.get(
            "/v1/companies/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_jobs_requires_auth(self, client):
        resp = await client.get("/v1/jobs")
        assert resp.status_code == 401
