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
    conclusions: list[str] = Field(default_factory=list)
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


class TranscriptSegment(BaseModel):
    """Represents a segment of speech by one speaker"""
    speaker: str = Field(description="Speaker label, e.g., 'S1', 'S2', or 'UU' for unknown")
    text: str
    start_time: Optional[float] = Field(default=None, description="Start time in seconds")
    end_time: Optional[float] = Field(default=None, description="End time in seconds")


class TranscribeResponse(BaseModel):
    """Response from /meetings/transcribe endpoint"""
    transcript_text: str = Field(description="Full plain text transcript")
    segments: list[TranscriptSegment] = Field(default_factory=list, description="Speaker-labeled segments")
    transcription_model: str
    trim: TrimInfo


class SummarizeRequest(BaseModel):
    """Request to /meetings/summarize endpoint"""
    transcript: str = Field(min_length=1, description="Transcript text to summarize")
    language: Optional[str] = Field(default=None, description="Language hint for better summarization")


class SummarizeResponse(BaseModel):
    """Response from /meetings/summarize endpoint"""
    notes: MeetingNotes
    llm_model: str


class MeetingProcessResponse(BaseModel):
    transcript: str
    notes: MeetingNotes
    model_info: ModelInfo
    trim: TrimInfo


class MeetingDocxRequest(BaseModel):
    meeting_title: Optional[str] = None
    transcript: str
    notes: MeetingNotes

