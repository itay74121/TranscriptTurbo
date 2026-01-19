from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    item: str = Field(min_length=1)
    owner: Optional[str] = None
    due_date: Optional[str] = Field(default=None, description="Optional date string (free-form or ISO).")


class MeetingNotes(BaseModel):
    summary: str = Field(min_length=1)
    participants: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)


class ModelInfo(BaseModel):
    transcription_model: str
    llm_model: str


class TrimInfo(BaseModel):
    requested: bool
    applied: bool
    method: Literal["frontend_ffmpeg_wasm", "backend_vad", "none"]
    error: Optional[str] = None


class MeetingProcessResponse(BaseModel):
    transcript: str
    notes: MeetingNotes
    model_info: ModelInfo
    trim: TrimInfo


class MeetingDocxRequest(BaseModel):
    meeting_title: Optional[str] = None
    transcript: str
    notes: MeetingNotes

