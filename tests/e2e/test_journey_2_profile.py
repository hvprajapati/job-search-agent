"""E2E Journey 2: Resume Upload → Profile Creation."""
import pytest
import io


class TestProfileJourney:
    async def test_get_profile_returns_404_when_empty(self, client, auth_headers):
        resp = await client.get("/v1/profile", headers=auth_headers)
        assert resp.status_code == 404

    async def test_upload_text_resume_creates_profile(self, client, auth_headers):
        resume_text = (
            "John Doe\nSenior Engineer\njohn@example.com\n555-0123\n\n"
            "Summary: Experienced Python developer with 8 years in fintech.\n\n"
            "Work History:\nStripe — Senior Engineer (2020-Present)\n"
            "Built payment APIs handling $1B+ annually.\n\n"
            "Education: BS Computer Science, MIT\n\n"
            "Skills: Python, FastAPI, PostgreSQL, Docker, AWS"
        )
        files = {"file": ("resume.txt", io.BytesIO(resume_text.encode()), "text/plain")}
        resp = await client.post(
            "/v1/profile/import/resume",
            files=files, data={"merge_strategy": "replace"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "profile_id" in data
        assert "parsed_fields" in data

    async def test_profile_populated_after_import(self, client, auth_headers):
        resp = await client.get("/v1/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["full_name"] != "" or data["headline"] != ""

    async def test_reject_unsupported_file_type(self, client, auth_headers):
        files = {"file": ("image.png", io.BytesIO(b"fake-png"), "image/png")}
        resp = await client.post(
            "/v1/profile/import/resume",
            files=files, data={"merge_strategy": "replace"},
            headers=auth_headers,
        )
        assert resp.status_code in (400, 422)

    async def test_reject_file_too_large(self, client, auth_headers):
        big_data = b"x" * (11 * 1024 * 1024)  # 11 MB
        files = {"file": ("big.txt", io.BytesIO(big_data), "text/plain")}
        resp = await client.post(
            "/v1/profile/import/resume",
            files=files, data={"merge_strategy": "replace"},
            headers=auth_headers,
        )
        assert resp.status_code in (400, 422)

    async def test_create_and_list_resumes(self, client, auth_headers):
        resp = await client.post("/v1/resumes", json={
            "name": "My Base Resume",
            "template_id": "modern_professional",
            "content": {"summary": "Experienced engineer with 5 years in backend systems."},
        }, headers=auth_headers)
        assert resp.status_code == 201

        resp = await client.get("/v1/resumes", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["name"] == "My Base Resume"
