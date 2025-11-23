"""Question endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Note: These are placeholder tests
# Full tests require setting up test data (subjects, topics, questions)


@pytest.mark.asyncio
async def test_list_questions_unauthorized(client: AsyncClient):
    """Test listing questions without authentication"""
    response = await client.get("/api/v1/questions")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_question_unauthorized(client: AsyncClient):
    """Test getting question detail without authentication"""
    # Use a random UUID
    question_id = "123e4567-e89b-12d3-a456-426614174000"
    response = await client.get(f"/api/v1/questions/{question_id}")
    
    assert response.status_code == 401


# TODO: Add authenticated tests with mock user and test data

