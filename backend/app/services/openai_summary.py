from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

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

        # Ensure base_url ends with /v1 for OpenAI SDK
        if base_url and not base_url.endswith("/v1"):
            base_url = f"{base_url.rstrip('/')}/v1"

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
            timeout=timeout_seconds,
        )
        self._model = model
        self._system_prompt = system_prompt

    async def summarize(self, *, transcript: str, language_hint: str | None = None) -> OpenAIResult:
        user_prompt = (
            "Transcript:\n"
            "-----\n"
            f"{transcript}\n"
            "-----\n"
        )
        if language_hint:
            user_prompt = f"Language hint: {language_hint}\n\n" + user_prompt

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "MeetingNotes",
                        "strict": True,
                        "schema": MEETING_NOTES_JSON_SCHEMA,
                    },
                },
            )
        except Exception as e:
            raise UpstreamError(f"OpenAI API call failed: {e!s}")

        # Extract the structured response
        choice = response.choices[0]

        # Check for refusal
        if choice.finish_reason == "content_filter" or (hasattr(choice.message, "refusal") and choice.message.refusal):
            refusal_msg = getattr(
                choice.message, "refusal", "Content filtered")
            raise UpstreamError(f"OpenAI refused: {refusal_msg}")

        # Parse the JSON content
        content = choice.message.content
        if not content:
            raise UpstreamError("OpenAI returned empty content")

        try:
            notes = MeetingNotes.model_validate_json(content)
        except Exception as e:
            raise UpstreamError(f"Failed to parse OpenAI response: {e!s}")

        return OpenAIResult(notes=notes, llm_model=response.model)
