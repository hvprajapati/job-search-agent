"""E2E Journey 1: Registration, Login, Logout."""
import pytest


class TestAuthJourney:
    async def test_register_creates_user_and_returns_tokens(self, client):
        resp = await client.post("/v1/auth/register", json={
            "email": "journey1@test.com",
            "password": "Test1234!",
            "full_name": "Journey One",
            "accept_terms": True,
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert data["user"]["email"] == "journey1@test.com"
        assert data["user"]["tier"] == "free"

    async def test_register_duplicate_email_rejected(self, client):
        await client.post("/v1/auth/register", json={
            "email": "dup@test.com", "password": "Test1234!",
            "full_name": "Dup User", "accept_terms": True,
        })
        resp = await client.post("/v1/auth/register", json={
            "email": "dup@test.com", "password": "Test1234!",
            "full_name": "Dup Again", "accept_terms": True,
        })
        assert resp.status_code == 409

    async def test_login_valid_credentials(self, client):
        await client.post("/v1/auth/register", json={
            "email": "login@test.com", "password": "Test1234!",
            "full_name": "Login Test", "accept_terms": True,
        })
        resp = await client.post("/v1/auth/login", json={
            "email": "login@test.com", "password": "Test1234!",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data["tokens"]

    async def test_login_invalid_password(self, client):
        await client.post("/v1/auth/register", json={
            "email": "badpw@test.com", "password": "Test1234!",
            "full_name": "Bad PW", "accept_terms": True,
        })
        resp = await client.post("/v1/auth/login", json={
            "email": "badpw@test.com", "password": "WrongPassword1!",
        })
        assert resp.status_code == 401

    async def test_logout_returns_204(self, client):
        await client.post("/v1/auth/register", json={
            "email": "logout@test.com", "password": "Test1234!",
            "full_name": "Logout Test", "accept_terms": True,
        })
        login_resp = await client.post("/v1/auth/login", json={
            "email": "logout@test.com", "password": "Test1234!",
        })
        token = login_resp.json()["data"]["tokens"]["access_token"]
        resp = await client.post("/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_protected_route_without_auth(self, client):
        resp = await client.get("/v1/profile")
        assert resp.status_code == 401

    async def test_register_weak_password_rejected(self, client):
        resp = await client.post("/v1/auth/register", json={
            "email": "weak@test.com", "password": "short",
            "full_name": "Weak PW", "accept_terms": True,
        })
        assert resp.status_code == 422
