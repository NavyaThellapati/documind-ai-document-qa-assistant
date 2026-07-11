from io import BytesIO


def test_chat_creation_question_sources_and_feedback(client, auth_headers):
    upload = client.post(
        "/api/documents/upload",
        headers=auth_headers,
        files={"file": ("guide.txt", BytesIO(b"The portal password reset link expires after 30 minutes."), "text/plain")},
    )
    doc_id = upload.json()["document"]["id"]

    conversation = client.post("/api/chat/conversations", headers=auth_headers, json={"title": "Portal help"})
    assert conversation.status_code == 201

    asked = client.post(
        "/api/chat/ask",
        headers=auth_headers,
        json={"conversation_id": conversation.json()["id"], "document_ids": [doc_id], "question": "When does the reset link expire?"},
    )
    assert asked.status_code == 200
    payload = asked.json()
    assert payload["sources"]
    assert payload["sources"][0]["document_name"] == "guide.txt"

    history = client.get(f"/api/chat/conversations/{payload['conversation_id']}", headers=auth_headers)
    assert len(history.json()["messages"]) == 1

    feedback = client.post("/api/feedback", headers=auth_headers, json={"message_id": payload["message_id"], "helpful": True, "comment": "Grounded answer"})
    assert feedback.status_code == 201


def test_missing_answer_behavior(client, auth_headers):
    client.post("/api/documents/upload", headers=auth_headers, files={"file": ("faq.txt", BytesIO(b"Clinic hours are 8 to 5."), "text/plain")})
    asked = client.post("/api/chat/ask", headers=auth_headers, json={"question": "unknown executive compensation?"})
    assert asked.status_code == 200
    assert "could not find" in asked.json()["answer"].lower()


def test_rename_and_delete_conversation(client, auth_headers):
    conversation = client.post("/api/chat/conversations", headers=auth_headers, json={"title": "Old"})
    cid = conversation.json()["id"]
    renamed = client.patch(f"/api/chat/conversations/{cid}", headers=auth_headers, json={"title": "New"})
    assert renamed.json()["title"] == "New"
    deleted = client.delete(f"/api/chat/conversations/{cid}", headers=auth_headers)
    assert deleted.status_code == 204
