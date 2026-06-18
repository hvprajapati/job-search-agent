"""E2E Journey 7: Resume Tailoring & Versioning."""
import pytest


class TestTailoringJourney:
    async def test_analyze_resume_requires_resume(self, client, auth_headers):
        resp = await client.post(
            "/v1/tailoring/analyze",
            params={
                "base_resume_id": "00000000-0000-0000-0000-000000000001",
                "job_id": "00000000-0000-0000-0000-000000000002",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_tailor_resume_requires_resume(self, client, auth_headers):
        resp = await client.post(
            "/v1/tailoring/tailor",
            params={
                "base_resume_id": "00000000-0000-0000-0000-000000000001",
                "job_id": "00000000-0000-0000-0000-000000000002",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_tailor_invalid_strategy_rejected(self, client, auth_headers):
        resp = await client.post(
            "/v1/tailoring/tailor",
            params={
                "base_resume_id": "00000000-0000-0000-0000-000000000001",
                "job_id": "00000000-0000-0000-0000-000000000002",
                "strategy": "invalid_strategy",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_versions_requires_auth(self, client):
        resp = await client.get(
            "/v1/tailoring/versions",
            params={
                "base_resume_id": "00000000-0000-0000-0000-000000000001",
                "job_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        assert resp.status_code == 401

    async def test_compare_requires_auth(self, client):
        resp = await client.get(
            "/v1/tailoring/compare",
            params={
                "version_a": "00000000-0000-0000-0000-000000000001",
                "version_b": "00000000-0000-0000-0000-000000000002",
            },
        )
        assert resp.status_code == 401

    async def test_accept_requires_auth(self, client):
        resp = await client.post(
            "/v1/tailoring/00000000-0000-0000-0000-000000000001/accept",
        )
        assert resp.status_code == 401

    async def test_tailor_with_valid_strategies(self, client, auth_headers):
        strategies = ["conservative", "moderate", "aggressive", "ats_only"]
        for s in strategies:
            resp = await client.post(
                "/v1/tailoring/tailor",
                params={
                    "base_resume_id": "00000000-0000-0000-0000-000000000001",
                    "job_id": "00000000-0000-0000-0000-000000000002",
                    "strategy": s,
                },
                headers=auth_headers,
            )
            assert resp.status_code in (200, 404)  # 404 if no resume, 200 if exists
