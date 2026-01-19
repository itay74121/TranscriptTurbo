import respx
import httpx


def _mock_speechmatics_success(respx_mock: respx.Router, *, job_id: str = "job_123", transcript: str = "hello world"):
    respx_mock.post("http://speechmatics.test/v2/jobs").mock(
        return_value=httpx.Response(201, json={"id": job_id})
    )
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}").mock(
        return_value=httpx.Response(
            200, json={"job": {"id": job_id, "status": "done"}})
    )
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}/transcript").mock(
        return_value=httpx.Response(200, text=transcript)
    )


def _mock_openai_success(respx_mock: respx.Router):
    respx_mock.post("http://openai.test/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "summary": "We discussed roadmap.",
                                "participants": ["Alice", "Bob"],
                                "decisions": ["Ship v1 next week"],
                                "action_items": [{"item": "Draft PRD", "owner": "Alice", "due_date": None}],
                            }
                        ],
                    }
                ]
            },
        )
    )


async def test_process_validation_rejects_unsupported_extension(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/process",
            files={"file": ("notes.txt", b"not audio", "text/plain")},
        )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["error"]


@respx.mock
async def test_process_success_returns_expected_shape(app, respx_mock: respx.Router):
    _mock_speechmatics_success(respx_mock)
    _mock_openai_success(respx_mock)

    wav_bytes = (
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00"
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/process",
            data={"trim_silence": "true",
                  "frontend_trimmed": "true", "language": "en"},
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()

    assert body["transcript"] == "hello world"
    assert body["notes"]["summary"] == "We discussed roadmap."
    assert body["notes"]["participants"] == ["Alice", "Bob"]
    assert body["notes"]["decisions"] == ["Ship v1 next week"]
    assert body["notes"]["action_items"][0]["item"] == "Draft PRD"
    assert body["trim"]["requested"] is True
    assert body["trim"]["applied"] is True
    assert body["trim"]["method"] == "frontend_ffmpeg_wasm"


@respx.mock
async def test_process_upstream_speechmatics_error(app, respx_mock: respx.Router):
    respx_mock.post("http://speechmatics.test/v2/jobs").mock(
        return_value=httpx.Response(401, json={"error": "no"}))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/process",
            files={"file": ("audio.wav", b"RIFF....", "audio/wav")},
        )
    assert resp.status_code == 502
    assert "Speechmatics create job failed" in resp.json()["error"]


@respx.mock
async def test_process_upstream_openai_error(app, respx_mock: respx.Router):
    _mock_speechmatics_success(respx_mock)
    respx_mock.post("http://openai.test/v1/responses").mock(
        return_value=httpx.Response(500, json={"error": "boom"}))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/process",
            files={"file": ("audio.wav", b"RIFF....", "audio/wav")},
        )
    assert resp.status_code == 502
    assert "OpenAI summarize failed" in resp.json()["error"]
