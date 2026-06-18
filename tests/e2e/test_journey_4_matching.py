"""E2E Journey 4: Job Matching & Feedback."""
import pytest


class TestMatchingJourney:
    async def test_compute_match_requires_profile(self, client, auth_headers):
        resp = await client.post(
            "/v1/match/compute",
            params={"job_id": "00000000-0000-0000-0000-000000000001"},
            headers=auth_headers,
        )
        assert resp.status_code in (404, 422)

    async def test_compute_match_requires_auth(self, client):
        resp = await client.post(
            "/v1/match/compute",
            params={"job_id": "00000000-0000-0000-0000-000000000001"},
        )
        assert resp.status_code == 401

    async def test_record_feedback_succeeds(self, client, auth_headers):
        resp = await client.post(
            "/v1/match/feedback",
            params={
                "job_id": "00000000-0000-0000-0000-000000000001",
                "feedback": "thumbs_up",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "feedback_recorded"

    async def test_record_feedback_invalid_value_rejected(self, client, auth_headers):
        resp = await client.post(
            "/v1/match/feedback",
            params={
                "job_id": "00000000-0000-0000-0000-000000000001",
                "feedback": "invalid_value",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_feedback_requires_auth(self, client):
        resp = await client.post(
            "/v1/match/feedback",
            params={
                "job_id": "00000000-0000-0000-0000-000000000001",
                "feedback": "thumbs_up",
            },
        )
        assert resp.status_code == 401
