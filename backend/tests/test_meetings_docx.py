import httpx


async def test_docx_validation_missing_notes_fields(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/meetings/docx", json={"transcript": "hi", "notes": {}})
    assert resp.status_code == 422


async def test_docx_success_returns_docx_bytes(app):
    payload = {
        "meeting_title": "Weekly Sync",
        "transcript": "Hello team",
        "notes": {
            "summary": "We aligned on priorities.",
            "participants": ["Alice"],
            "decisions": ["Do X"],
            "action_items": [{"item": "Follow up", "owner": None, "due_date": None}],
        },
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/meetings/docx", json=payload)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "attachment" in resp.headers.get("content-disposition", "")
    # DOCX is a ZIP file; starts with PK
    assert resp.content[:2] == b"PK"

