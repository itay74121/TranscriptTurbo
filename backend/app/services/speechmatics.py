from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.errors import BadRequestError, UpstreamError, UpstreamTimeoutError
from app.models import TranscriptSegment


@dataclass(frozen=True)
class SpeechmaticsResult:
    transcript_text: str
    transcription_model: str
    segments: list[TranscriptSegment]


class SpeechmaticsClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        poll_interval_seconds: float,
        poll_timeout_seconds: float,
    ):
        if not api_key:
            raise BadRequestError("SPEECHMATICS_API_KEY is not configured.")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._poll_timeout = poll_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def transcribe_file(
        self,
        *,
        file_path: str,
        original_filename: str,
        language: str,
    ) -> SpeechmaticsResult:
        job_id = await self._create_job(file_path=file_path, original_filename=original_filename, language=language)
        await self._wait_for_done(job_id)
        transcript = await self._fetch_transcript_text(job_id)
        segments = await self._fetch_transcript_segments(job_id)
        # Speechmatics doesn't expose a single model string like OpenAI; we return a stable identifier.
        return SpeechmaticsResult(
            transcript_text=transcript, 
            transcription_model="speechmatics-batch-v2",
            segments=segments
        )

    async def _create_job(self, *, file_path: str, original_filename: str, language: str) -> str:
        url = f"{self._base_url}/v2/jobs"

        # Basic config without diarization (more compatible with different Speechmatics plans)
        config = {
            "type": "transcription",
            "transcription_config": {
                "language": language,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            with open(file_path, "rb") as f:
                files = {
                    "data_file": (original_filename, f, "application/octet-stream"),
                    "config": (None, json.dumps(config), "application/json"),
                }
                resp = await client.post(url, headers=self._headers(), files=files)

        if resp.status_code not in (200, 201):
            raise UpstreamError(f"Speechmatics create job failed ({resp.status_code}).", status_code=resp.status_code)

        data = resp.json()
        job_id = data.get("id")
        if not job_id:
            raise UpstreamError("Speechmatics create job response missing job id.")
        return str(job_id)

    async def _wait_for_done(self, job_id: str) -> None:
        url = f"{self._base_url}/v2/jobs/{job_id}"
        deadline = asyncio.get_event_loop().time() + self._poll_timeout

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                if asyncio.get_event_loop().time() > deadline:
                    raise UpstreamTimeoutError("Speechmatics transcription timed out while polling job status.")

                resp = await client.get(url, headers=self._headers())
                if resp.status_code != 200:
                    raise UpstreamError(
                        f"Speechmatics job status failed ({resp.status_code}).", status_code=resp.status_code
                    )

                payload = resp.json()
                # docs show { "job": { "status": "running|done|rejected|..." } }
                job = payload.get("job") or payload
                status = (job.get("status") or "").lower()

                if status == "done":
                    return
                if status in ("rejected", "deleted", "expired"):
                    raise UpstreamError(f"Speechmatics job ended with status={status}.")

                await asyncio.sleep(self._poll_interval)

    async def _fetch_transcript_text(self, job_id: str) -> str:
        url = f"{self._base_url}/v2/jobs/{job_id}/transcript"
        params = {"format": "txt"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)

        if resp.status_code != 200:
            raise UpstreamError(f"Speechmatics transcript fetch failed ({resp.status_code}).", status_code=resp.status_code)

        text = resp.text.strip()
        if not text:
            # allow empty but keep consistent type
            return ""
        return text

    async def _fetch_transcript_segments(self, job_id: str) -> list[TranscriptSegment]:
        """
        Fetch transcript in JSON format to extract speaker-labeled segments.
        Falls back to single segment if speaker diarization is not available.
        """
        url = f"{self._base_url}/v2/jobs/{job_id}/transcript"
        params = {"format": "json-v2"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers(), params=params)

            if resp.status_code != 200:
                # If JSON format fails, return empty segments (will fall back to plain text)
                return []

            data = resp.json()
        except Exception:
            # If parsing fails, return empty segments
            return []

        # Parse the JSON response to extract speaker segments
        segments: list[TranscriptSegment] = []
        results = data.get("results", [])
        
        if not results:
            return []
        
        current_speaker = None
        current_text = []
        current_start = None
        prev_end_time = None
        
        for result in results:
            if result.get("type") == "word":
                word_text = result.get("alternatives", [{}])[0].get("content", "")
                # Speaker might not be present if diarization is not enabled
                speaker = result.get("speaker", "Speaker")
                start_time = result.get("start_time")
                end_time = result.get("end_time")
                
                # If speaker changes, save the previous segment
                if current_speaker is not None and speaker != current_speaker:
                    if current_text:
                        segments.append(TranscriptSegment(
                            speaker=current_speaker,
                            text=" ".join(current_text),
                            start_time=current_start,
                            end_time=prev_end_time
                        ))
                    current_text = []
                    current_start = start_time
                
                # Initialize or update current segment
                if not current_text:
                    current_start = start_time
                    current_speaker = speaker
                
                current_text.append(word_text)
                prev_end_time = end_time
        
        # Add the last segment
        if current_text and current_speaker is not None:
            segments.append(TranscriptSegment(
                speaker=current_speaker,
                text=" ".join(current_text),
                start_time=current_start,
                end_time=prev_end_time
            ))
        
        return segments

