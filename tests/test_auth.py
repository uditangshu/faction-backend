"""Authentication endpoint tests"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_initiation(client: AsyncClient, test_user_data):
    """Test signup initiation endpoint"""
    response = await client.post("/api/v1/auth/signup", json=test_user_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "temp_token" in data
    assert data["otp_sent"] is True
    assert data["expires_in"] == 300


@pytest.mark.asyncio
async def test_signup_duplicate_phone(client: AsyncClient, test_user_data):
    """Test signup with duplicate phone number"""
    # First signup
    response1 = await client.post("/api/v1/auth/signup", json=test_user_data)
    assert response1.status_code == 200
    
    # Get OTP and complete signup
    temp_token = response1.json()["temp_token"]
    # Note: In mock mode, OTP is printed to console but we can use any 6-digit code for testing
    verify_response = await client.post(
        "/api/v1/auth/verify-signup",
        json={"temp_token": temp_token, "otp": "123456"}
    )
    
    # Try to signup again with same phone
    response2 = await client.post("/api/v1/auth/signup", json=test_user_data)
    assert response2.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent phone number"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919999999999"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint"""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Faction Digital Backend API"
    assert "version" in data

