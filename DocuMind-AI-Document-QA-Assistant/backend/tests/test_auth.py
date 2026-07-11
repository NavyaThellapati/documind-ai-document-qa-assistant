def test_register_login_and_profile(client):
    created = client.post("/api/auth/register", json={"email": "new@example.com", "password": "strongpass123", "full_name": "New User"})
    assert created.status_code == 201
    assert created.json()["user"]["email"] == "new@example.com"

    logged_in = client.post("/api/auth/login", json={"email": "new@example.com", "password": "strongpass123"})
    assert logged_in.status_code == 200

    profile = client.get("/api/auth/me", headers={"Authorization": f"Bearer {logged_in.json()['access_token']}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "new@example.com"


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/documents")
    assert response.status_code in {401, 403}
