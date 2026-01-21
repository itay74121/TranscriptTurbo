from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from app.core.config import get_settings
from app.core.errors import BadRequestError, UpstreamError, UpstreamTimeoutError
from app.models import MeetingDocxRequest, MeetingProcessResponse, ModelInfo, TrimInfo
from app.services.openai_summary import OpenAISummarizer
from app.services.speechmatics import SpeechmaticsClient
from app.utils.audio_trim import trim_silence_vad
from app.utils.docx_builder import build_meeting_docx
from app.utils.uploads import save_upload_to_tempfile, validate_audio_filename


router = APIRouter()


@router.post("/meetings/process", response_model=MeetingProcessResponse)
async def process_meeting(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    meeting_title: Optional[str] = Form(None),
    trim_silence: Optional[bool] = Form(None),
    frontend_trimmed: Optional[bool] = Form(None),
):
    settings = get_settings()

    if not file.filename:
        raise BadRequestError("Missing filename.")
    validate_audio_filename(file.filename)

    # Defaults
    if trim_silence is None:
        trim_silence = settings.trim_silence_default
    if frontend_trimmed is None:
        frontend_trimmed = False
    lang = language or settings.speechmatics_language

    temp_path = await save_upload_to_tempfile(file, max_bytes=settings.max_upload_bytes)
    active_path = temp_path
    trim_info = TrimInfo(requested=bool(trim_silence),
                         applied=False, method="none", error=None)

    try:
        if trim_silence and not frontend_trimmed:
            tr = trim_silence_vad(temp_path)
            if tr.applied:
                active_path = tr.output_path
                trim_info = TrimInfo(
                    requested=True, applied=True, method="backend_vad", error=None)
            else:
                trim_info = TrimInfo(
                    requested=True, applied=False, method="none", error=tr.error)
        elif trim_silence and frontend_trimmed:
            trim_info = TrimInfo(requested=True, applied=True,
                                 method="frontend_ffmpeg_wasm", error=None)
        print('key: ' + settings.speechmatics_api_key)
        speech = SpeechmaticsClient(
            base_url=settings.speechmatics_base_url,
            api_key=settings.speechmatics_api_key,
            timeout_seconds=settings.request_timeout_seconds,
            poll_interval_seconds=settings.speechmatics_poll_interval_seconds,
            poll_timeout_seconds=settings.speechmatics_poll_timeout_seconds,
        )
        speech_res = await speech.transcribe_file(
            file_path=active_path, original_filename=file.filename, language=lang
        )

        system_prompt_path = Path(__file__).resolve(
        ).parents[2] / "prompts" / "meeting_summary_system.txt"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")
        print(f'key2: {settings.openai_api_key}')
        summarizer = OpenAISummarizer(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.request_timeout_seconds,
            system_prompt=system_prompt,
        )
        summary_res = await summarizer.summarize(transcript=speech_res.transcript_text, language_hint=lang)

        return MeetingProcessResponse(
            transcript=speech_res.transcript_text,
            notes=summary_res.notes,
            model_info=ModelInfo(
                transcription_model=speech_res.transcription_model, llm_model=summary_res.llm_model),
            trim=trim_info,
        )
    except (BadRequestError, UpstreamError, UpstreamTimeoutError):
        raise
    finally:
        # Cleanup temp files
        for p in {temp_path, active_path}:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


@router.post("/meetings/docx")
async def meeting_docx(req: MeetingDocxRequest):
    docx_bytes = build_meeting_docx(req)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="meeting-notes.docx"'},
    )
