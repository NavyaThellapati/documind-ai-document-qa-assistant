from io import BytesIO


def upload_txt(client, headers, name="handbook.txt", text="Vacation policy allows 15 days of paid time off."):
    return client.post("/api/documents/upload", headers=headers, files={"file": (name, BytesIO(text.encode()), "text/plain")})


def test_file_validation_rejects_unsupported(client, auth_headers):
    response = client.post("/api/documents/upload", headers=auth_headers, files={"file": ("bad.exe", BytesIO(b"bad"), "application/octet-stream")})
    assert response.status_code == 400


def test_document_upload_list_detail_delete(client, auth_headers):
    response = upload_txt(client, auth_headers)
    assert response.status_code == 201
    document = response.json()["document"]
    assert document["status"] == "processed"
    assert document["chunk_count"] >= 1

    listed = client.get("/api/documents", headers=auth_headers)
    assert len(listed.json()["documents"]) == 1

    detail = client.get(f"/api/documents/{document['id']}", headers=auth_headers)
    assert detail.status_code == 200

    deleted = client.delete(f"/api/documents/{document['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/documents/{document['id']}", headers=auth_headers).status_code == 404


def test_duplicate_upload_not_reprocessed(client, auth_headers):
    first = upload_txt(client, auth_headers)
    second = upload_txt(client, auth_headers)
    assert first.status_code == 201
    assert second.json()["duplicate"] is True


def test_user_access_isolation(client, auth_headers):
    doc = upload_txt(client, auth_headers).json()["document"]
    other = client.post("/api/auth/register", json={"email": "other@example.com", "password": "Strongpass123"}).json()["access_token"]
    response = client.get(f"/api/documents/{doc['id']}", headers={"Authorization": f"Bearer {other}"})
    assert response.status_code == 404
