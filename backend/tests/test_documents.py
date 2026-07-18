from io import BytesIO

from docx import Document as DocxDocument


def upload_txt(client, headers, name="handbook.txt", text="Vacation policy allows 15 days of paid time off."):
    return client.post("/api/documents/upload", headers=headers, files={"file": (name, BytesIO(text.encode()), "text/plain")})


def docx_bytes(text: str) -> BytesIO:
    document = DocxDocument()
    for paragraph in text.split("\n"):
        document.add_paragraph(paragraph)
    stream = BytesIO()
    document.save(stream)
    stream.seek(0)
    return stream


def simple_pdf_bytes(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >> stream\n" + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj ".encode() + obj + b" endobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    return bytes(pdf)


def test_file_validation_rejects_unsupported(client, auth_headers):
    response = client.post("/api/documents/upload", headers=auth_headers, files={"file": ("bad.exe", BytesIO(b"bad"), "application/octet-stream")})
    assert response.status_code == 400


def test_download_requires_authentication(client, auth_headers):
    document = upload_txt(client, auth_headers).json()["document"]
    response = client.get(f"/api/documents/{document['id']}/download")
    assert response.status_code in {401, 403}


def test_document_upload_list_detail_delete(client, auth_headers):
    response = upload_txt(client, auth_headers)
    assert response.status_code == 201
    document = response.json()["document"]
    assert document["status"] == "queued"
    assert document["processing_progress"] == 25
    assert document["file_type"] == "txt"

    listed = client.get("/api/documents", headers=auth_headers)
    assert len(listed.json()["documents"]) == 1

    detail = client.get(f"/api/documents/{document['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"
    assert detail.json()["processing_progress"] == 100
    assert detail.json()["chunk_count"] >= 1

    deleted = client.delete(f"/api/documents/{document['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/documents/{document['id']}", headers=auth_headers).status_code == 404


def test_duplicate_upload_not_reprocessed(client, auth_headers):
    first = upload_txt(client, auth_headers)
    second = upload_txt(client, auth_headers)
    assert first.status_code == 201
    assert second.json()["duplicate"] is True


def test_background_reprocess_returns_queued_status(client, auth_headers):
    document = upload_txt(client, auth_headers).json()["document"]

    response = client.post(f"/api/documents/{document['id']}/reprocess/background", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_same_name_different_content_gets_unique_storage_path(client, auth_headers):
    first = upload_txt(client, auth_headers, name="policy.txt", text="First policy text.")
    second = upload_txt(client, auth_headers, name="policy.txt", text="Second policy text.")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["document"]["id"] != second.json()["document"]["id"]


def test_user_access_isolation(client, auth_headers):
    doc = upload_txt(client, auth_headers).json()["document"]
    other = client.post("/api/auth/register", json={"email": "other@example.com", "password": "Strongpass123"}).json()["access_token"]
    response = client.get(f"/api/documents/{doc['id']}", headers={"Authorization": f"Bearer {other}"})
    assert response.status_code == 404


def test_document_explanation_is_grounded_cached_and_specific(client, auth_headers):
    resume = """
Professional Summary
Python backend engineer building AI document platforms.

Technical Skills
- Python
- FastAPI
- PostgreSQL
- Docker

Experience
Accenture Software Engineer, 2021 to 2024.

Projects
DocuMind uses RAG, ChromaDB, and OpenAI for document question answering.
"""
    document = upload_txt(client, auth_headers, name="resume.txt", text=resume).json()["document"]

    response = client.post(f"/api/documents/{document['id']}/explain", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document["id"]
    assert payload["status"] == "ready"
    assert "resume" in payload["overview"].lower()
    assert "Python" in payload["key_entities"]
    assert "Professional Summary" in payload["main_sections"]
    assert any("backend technologies" in question for question in payload["suggested_questions"])
    assert payload["sources"]

    cached = client.get(f"/api/documents/{document['id']}/insight", headers=auth_headers)
    assert cached.status_code == 200
    assert cached.json()["id"] == payload["id"]


def test_document_explanation_reports_missing_llm_key(client, auth_headers):
    document = upload_txt(client, auth_headers).json()["document"]

    response = client.get(f"/api/documents/{document['id']}/insight", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["llm_configured"] is False
    assert "LLM API key" in response.json()["notice"]


def test_document_explanation_authorization(client, auth_headers):
    document = upload_txt(client, auth_headers).json()["document"]
    other = client.post("/api/auth/register", json={"email": "summary-other@example.com", "password": "Strongpass123"}).json()["access_token"]

    response = client.get(f"/api/documents/{document['id']}/insight", headers={"Authorization": f"Bearer {other}"})

    assert response.status_code == 404


def test_explanation_flow_supports_txt_docx_and_pdf(client, auth_headers):
    cases = [
        ("resume.txt", BytesIO(b"Professional Summary\nPython FastAPI engineer.\n\nProjects\nDocuMind RAG assistant."), "text/plain", "resume"),
        ("guide.docx", docx_bytes("User Guide\nInstall the healthcare portal.\nTroubleshooting\nReset login credentials."), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "guide"),
        ("resume.pdf", BytesIO(simple_pdf_bytes("Resume Professional Summary Python FastAPI Projects DocuMind")), "application/pdf", "resume"),
        ("policy.pdf", BytesIO(simple_pdf_bytes("Policy Page One Remote work requires approval. Policy Page Two Compliance dates are listed.")), "application/pdf", "policy"),
    ]

    for filename, file_obj, content_type, expected_kind in cases:
        uploaded = client.post("/api/documents/upload", headers=auth_headers, files={"file": (filename, file_obj, content_type)})
        assert uploaded.status_code == 201
        document = uploaded.json()["document"]

        preview = client.get(f"/api/documents/{document['id']}/preview", headers=auth_headers)
        assert preview.status_code == 200
        assert preview.json()["chunks"]
        assert preview.json()["chunks"][0]["text"][0].isalnum()

        insight = client.post(f"/api/documents/{document['id']}/explain", headers=auth_headers)
        assert insight.status_code == 200
        assert expected_kind in insight.json()["overview"].lower()
        assert insight.json()["suggested_questions"]
