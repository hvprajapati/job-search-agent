"""E2E Journey 5: Agent Execution & Memory."""
import pytest


class TestAgentJourney:
    async def test_agent_execute_returns_response(self, client, auth_headers):
        resp = await client.post("/v1/agent/execute", json={
            "message": "find me python jobs",
            "stream": False,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "response" in data
        assert len(data["response"]) > 10

    async def test_agent_general_question(self, client, auth_headers):
        resp = await client.post("/v1/agent/execute", json={
            "message": "Hello! What can you help me with?",
            "stream": False,
        }, headers=auth_headers)
        assert resp.status_code == 200
        response = resp.json()["data"]["response"]
        assert len(response) > 10

    async def test_agent_execution_history(self, client, auth_headers):
        # Execute an agent call first to create history
        await client.post("/v1/agent/execute", json={
            "message": "test query for history",
            "stream": False,
        }, headers=auth_headers)

        resp = await client.get("/v1/agent/executions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data

    async def test_agent_execution_detail_not_found(self, client, auth_headers):
        resp = await client.get(
            "/v1/agent/executions/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_agent_execute_requires_auth(self, client):
        resp = await client.post("/v1/agent/execute", json={
            "message": "hello",
            "stream": False,
        })
        assert resp.status_code == 401

    async def test_agent_empty_message_handled(self, client, auth_headers):
        resp = await client.post("/v1/agent/execute", json={
            "message": "",
            "stream": False,
        }, headers=auth_headers)
        assert resp.status_code == 200
        response = resp.json()["data"]["response"]
        assert len(response) > 5
