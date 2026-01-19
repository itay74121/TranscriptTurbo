from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.errors import BadRequestError


ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}


def validate_audio_filename(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestError(f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}")


async def save_upload_to_tempfile(upload: UploadFile, *, max_bytes: int) -> str:
    # Create temp file using original suffix for easier decoding.
    suffix = Path(upload.filename or "").suffix or ".bin"
    fd, path = tempfile.mkstemp(prefix="transcriptturbo_", suffix=suffix)
    os.close(fd)

    total = 0
    try:
        with open(path, "wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise BadRequestError(f"File too large. Max allowed is {max_bytes} bytes.")
                out.write(chunk)
    finally:
        await upload.close()

    return path

