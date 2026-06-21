import pytest

@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    # 1. Register a new user
    user_data = {
        "name": "Alex Admin",
        "email": "alex.admin@example.com",
        "password": "securepassword99"
    }
    
    response = await client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["email"] == user_data["email"]
    assert json_data["name"] == user_data["name"]
    assert "password_hash" not in json_data
    
    # 2. Login
    login_data = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    response = await client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    # 3. Access protected route /me
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await client.get("/api/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == user_data["email"]

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    login_data = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = await client.post("/api/auth/login", json=login_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_settings(authenticated_client):
    # Get settings
    settings_response = await authenticated_client.get("/api/auth/settings")
    assert settings_response.status_code == 200
    settings_data = settings_response.json()
    assert settings_data["theme"] == "dark"  # Default
    
    # Update settings
    update_data = {
        "theme": "light",
        "model_preferences": {
            "primary_model": "ollama",
            "temperature": 0.2
        }
    }
    update_response = await authenticated_client.put("/api/auth/settings", json=update_data)
    assert update_response.status_code == 200
    
    # Verify change
    settings_response = await authenticated_client.get("/api/auth/settings")
    assert settings_response.status_code == 200
    updated_data = settings_response.json()
    assert updated_data["theme"] == "light"
    assert updated_data["model_preferences"]["primary_model"] == "ollama"
    assert updated_data["model_preferences"]["temperature"] == 0.2
