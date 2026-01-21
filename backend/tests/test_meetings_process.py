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
    # Mock text format response
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}/transcript", params={"format": "txt"}).mock(
        return_value=httpx.Response(200, text=transcript)
    )
    # Mock JSON format response with speaker diarization
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}/transcript", params={"format": "json-v2"}).mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"type": "word", "alternatives": [
                    {"content": "hello"}], "speaker": "S1", "start_time": 0.0, "end_time": 0.5},
                {"type": "word", "alternatives": [
                    {"content": "world"}], "speaker": "S1", "start_time": 0.6, "end_time": 1.0},
            ]
        })
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


# Tests for new decoupled endpoints


@respx.mock
async def test_transcribe_success_with_diarization(app, respx_mock: respx.Router):
    """Test /meetings/transcribe endpoint returns transcript with speaker segments"""
    _mock_speechmatics_success(
        respx_mock, transcript="hello world from speakers")

    wav_bytes = (
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00"
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/transcribe",
            data={"language": "en"},
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()

    assert body["transcript_text"] == "hello world from speakers"
    assert body["transcription_model"] == "speechmatics-batch-v2"
    assert "segments" in body
    assert len(body["segments"]) == 1  # Two words from same speaker grouped
    assert body["segments"][0]["speaker"] == "S1"
    assert body["segments"][0]["text"] == "hello world"
    assert "trim" in body


@respx.mock
async def test_transcribe_multiple_speakers(app, respx_mock: respx.Router):
    """Test transcription with multiple speakers"""
    job_id = "job_multi"
    respx_mock.post("http://speechmatics.test/v2/jobs").mock(
        return_value=httpx.Response(201, json={"id": job_id})
    )
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}").mock(
        return_value=httpx.Response(
            200, json={"job": {"id": job_id, "status": "done"}})
    )
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}/transcript", params={"format": "txt"}).mock(
        return_value=httpx.Response(200, text="Hello there How are you")
    )
    respx_mock.get(f"http://speechmatics.test/v2/jobs/{job_id}/transcript", params={"format": "json-v2"}).mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"type": "word", "alternatives": [
                    {"content": "Hello"}], "speaker": "S1", "start_time": 0.0, "end_time": 0.5},
                {"type": "word", "alternatives": [
                    {"content": "there"}], "speaker": "S1", "start_time": 0.6, "end_time": 1.0},
                {"type": "word", "alternatives": [
                    {"content": "How"}], "speaker": "S2", "start_time": 1.1, "end_time": 1.5},
                {"type": "word", "alternatives": [
                    {"content": "are"}], "speaker": "S2", "start_time": 1.6, "end_time": 1.8},
                {"type": "word", "alternatives": [
                    {"content": "you"}], "speaker": "S2", "start_time": 1.9, "end_time": 2.2},
            ]
        })
    )

    wav_bytes = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/transcribe",
            files={"file": ("meeting.wav", wav_bytes, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()

    assert len(body["segments"]) == 2
    assert body["segments"][0]["speaker"] == "S1"
    assert body["segments"][0]["text"] == "Hello there"
    assert body["segments"][1]["speaker"] == "S2"
    assert body["segments"][1]["text"] == "How are you"


@respx.mock
async def test_summarize_success(app, respx_mock: respx.Router):
    """Test /meetings/summarize endpoint accepts transcript and returns summary"""
    respx_mock.post("http://openai.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary": "Team sync meeting", "participants": ["Alice", "Bob"], "decisions": ["Launch next week"], "action_items": [{"item": "Prepare demo", "owner": "Alice", "due_date": "2024-01-15"}]}'
                        },
                        "finish_reason": "stop"
                    }
                ],
                "model": "gpt-4"
            },
        )
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/summarize",
            json={
                "transcript": "Alice: Hello Bob. Bob: Hi Alice, ready for launch? Alice: Yes, let's do it next week.",
                "language": "en"
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    assert body["llm_model"] == "gpt-4"
    assert body["notes"]["summary"] == "Team sync meeting"
    assert "Alice" in body["notes"]["participants"]
    assert "Bob" in body["notes"]["participants"]
    assert len(body["notes"]["decisions"]) == 1
    assert len(body["notes"]["action_items"]) == 1


@respx.mock
async def test_transcribe_succeeds_even_when_used_independently(app, respx_mock: respx.Router):
    """Test that transcribe endpoint works independently and doesn't require summarization"""
    _mock_speechmatics_success(
        respx_mock, transcript="independent transcript test")

    wav_bytes = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/transcribe",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript_text"] == "independent transcript test"
    # No summarization was attempted - this proves decoupling


@respx.mock
async def test_transcribe_validation_rejects_unsupported_extension(app):
    """Test that transcribe endpoint validates file types"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/meetings/transcribe",
            files={"file": ("document.pdf", b"fake pdf", "application/pdf")},
        )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["error"]
