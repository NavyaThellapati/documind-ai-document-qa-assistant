def test_register_login_and_profile(client):
    created = client.post("/api/auth/register", json={"email": "new@example.com", "password": "Strongpass123", "full_name": "New User"})
    assert created.status_code == 201
    assert created.json()["user"]["email"] == "new@example.com"

    logged_in = client.post("/api/auth/login", json={"email": "new@example.com", "password": "Strongpass123"})
    assert logged_in.status_code == 200

    profile = client.get("/api/auth/me", headers={"Authorization": f"Bearer {logged_in.json()['access_token']}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "new@example.com"


def test_refresh_and_logout(client):
    created = client.post("/api/auth/register", json={"email": "refresh@example.com", "password": "Strongpass123"})
    refresh_token = created.json()["refresh_token"]
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert logout.status_code == 204


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/documents")
    assert response.status_code in {401, 403}


def test_auth_rate_limit_rejects_excess_attempts(client):
    for _ in range(10):
        response = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "Wrongpass123"})
        assert response.status_code == 401

    limited = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "Wrongpass123"})
    assert limited.status_code == 429
