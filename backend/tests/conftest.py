import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.database.mongodb import db_client, connect_to_mongo, close_mongo_connection

# Force test database settings
settings.MONGODB_DB_NAME = "test_chatbot_rag"
settings.JWT_SECRET_KEY = "testsecretkeytestsecretkeytestsecretkey"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    # Run startup
    await connect_to_mongo()
    
    # Empty test database before running tests
    db = db_client.db
    collections = await db.list_collection_names()
    for col in collections:
        await db[col].delete_many({})
        
    yield
    
    # Cleanup after tests
    db = db_client.db
    collections = await db.list_collection_names()
    for col in collections:
        await db[col].delete_many({})
    await close_mongo_connection()

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def authenticated_client(client):
    # Register and login a test user
    user_payload = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "testpassword123"
    }
    
    # Register
    reg_response = await client.post("/api/auth/register", json=user_payload)
    if reg_response.status_code not in (201, 400):
        raise RuntimeError(f"Failed to setup test user: {reg_response.text}")
        
    # Login
    login_response = await client.post("/api/auth/login", json={
        "email": user_payload["email"],
        "password": user_payload["password"]
    })
    token_data = login_response.json()
    token = token_data["access_token"]
    
    # Set authorization header
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
