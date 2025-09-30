"""
Tests for the Claude Agent SDK API Server
"""

import pytest
from httpx import AsyncClient
from claude_agent_sdk.api_server import app


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_sessions" in data


@pytest.mark.asyncio
async def test_create_session():
    """Test session creation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/sessions", json={})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["message"] == "Session created successfully"


@pytest.mark.asyncio
async def test_list_sessions():
    """Test listing sessions"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a session first
        create_response = await client.post("/sessions", json={})
        assert create_response.status_code == 200
        
        # List sessions
        list_response = await client.get("/sessions")
        assert list_response.status_code == 200
        data = list_response.json()
        assert "sessions" in data
        assert data["count"] >= 1


@pytest.mark.asyncio
async def test_delete_session():
    """Test session deletion"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]
        
        # Delete the session
        delete_response = await client.delete(f"/sessions/{session_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_query_nonexistent_session():
    """Test querying a non-existent session"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/sessions/nonexistent-id/query",
            json={"prompt": "Hello", "stream": False}
        )
        assert response.status_code == 404
