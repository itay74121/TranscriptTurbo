from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.core.errors import BadRequestError, UpstreamError
from app.models import MeetingNotes


@dataclass(frozen=True)
class OpenAIResult:
    notes: MeetingNotes
    llm_model: str


MEETING_NOTES_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "participants": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "item": {"type": "string"},
                    "owner": {"type": ["string", "null"]},
                    "due_date": {"type": ["string", "null"]},
                },
                "required": ["item", "owner", "due_date"],
            },
        },
    },
    "required": ["summary", "participants", "decisions", "action_items"],
}


class OpenAISummarizer:
    def __init__(self, *, base_url: str, api_key: str, model: str, timeout_seconds: float, system_prompt: str):
        if not api_key:
            raise BadRequestError("OPENAI_API_KEY is not configured.")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._system_prompt = system_prompt

    async def summarize(self, *, transcript: str, language_hint: str | None = None) -> OpenAIResult:
        url = f"{self._base_url}/v1/responses"

        user_prompt = (
            "Transcript:\n"
            "-----\n"
            f"{transcript}\n"
            "-----\n"
        )
        if language_hint:
            user_prompt = f"Language hint: {language_hint}\n\n" + user_prompt

        payload = {
            "model": self._model,
            "input": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "MeetingNotes",
                    "strict": True,
                    "schema": MEETING_NOTES_JSON_SCHEMA,
                }
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)

        if resp.status_code != 200:
            raise UpstreamError(f"OpenAI summarize failed ({resp.status_code}).", status_code=resp.status_code)

        data = resp.json()
        # Expected: output[0].content[0] is the structured object.
        try:
            output = data["output"]
            msg = next(item for item in output if item.get("type") == "message")
            content = msg["content"]
            obj = content[0]
        except Exception as e:  # noqa: BLE001 - keep robust for upstream changes
            raise UpstreamError(f"OpenAI response parsing failed: {e!s}")

        # If refusal, surface it cleanly
        if isinstance(obj, dict) and obj.get("type") == "refusal":
            raise UpstreamError(f"OpenAI refused: {obj.get('refusal', 'unknown refusal')}")

        # Ensure dict; if string, try JSON parse (defensive)
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except Exception as e:  # noqa: BLE001
                raise UpstreamError(f"OpenAI returned non-JSON content: {e!s}")

        notes = MeetingNotes.model_validate(obj)
        return OpenAIResult(notes=notes, llm_model=self._model)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

