from io import BytesIO


def upload_doc(client, headers):
    return client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("policy.txt", BytesIO(b"Remote work is allowed three days per week with manager approval."), "text/plain")},
    ).json()["document"]


def test_dashboard_health_document_search_and_download(client, auth_headers):
    document = upload_doc(client, auth_headers)

    dashboard = client.get("/api/dashboard/summary", headers=auth_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_documents"] == 1
    assert dashboard.json()["storage_used_bytes"] > 0

    health = client.get("/api/health")
    assert health.status_code == 200
    assert "database" in health.json()["checks"]

    search = client.get(f"/api/documents/{document['id']}/search?query=remote", headers=auth_headers)
    assert search.status_code == 200
    assert search.json()["results"]

    preview = client.get(f"/api/documents/{document['id']}/preview", headers=auth_headers)
    assert preview.status_code == 200
    assert preview.json()["chunks"]

    download = client.get(f"/api/documents/{document['id']}/download", headers=auth_headers)
    assert download.status_code == 200
    assert b"Remote work" in download.content


def test_streaming_chat_endpoint(client, auth_headers):
    document = upload_doc(client, auth_headers)
    with client.stream(
        "POST",
        "/api/chat/ask/stream",
        headers=auth_headers,
        json={"question": "How many remote work days are allowed?", "document_ids": [document["id"]]},
    ) as response:
        body = response.read().decode()
    assert response.status_code == 200
    assert "event: token" in body
    assert "event: done" in body
