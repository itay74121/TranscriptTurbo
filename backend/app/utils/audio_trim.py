from __future__ import annotations

import contextlib
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import BadRequestError


@dataclass(frozen=True)
class TrimResult:
    applied: bool
    method: str  # "backend_vad" | "none"
    output_path: str
    error: str | None = None


def _optional_import(name: str):
    try:
        module = __import__(name)
        return module
    except Exception:  # noqa: BLE001
        return None


def _write_wav_pcm16(path: str, *, pcm16: bytes, sample_rate: int, channels: int) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)


def _decode_to_pcm16_mono_16k(input_path: str) -> bytes:
    """
    Best-effort decode. Requires miniaudio for mp3/m4a; wav may work via miniaudio too.
    Returns raw PCM16LE mono 16k bytes.
    """
    miniaudio = _optional_import("miniaudio")
    if not miniaudio:
        raise BadRequestError("Backend trim requires 'miniaudio' dependency (not available).")

    decoded = miniaudio.decode_file(
        input_path,
        sample_rate=16000,
        nchannels=1,
        sample_format=miniaudio.SampleFormat.SIGNED16,
    )
    return decoded.samples.tobytes()


def trim_silence_vad(input_path: str) -> TrimResult:
    """
    Best-effort VAD trimming:
    - decode to 16kHz mono PCM16
    - run webrtcvad over 30ms frames
    - keep speech frames plus a little padding
    - output a WAV (pcm16, 16k mono)

    If anything fails, returns applied=False and output_path=input_path.
    """
    webrtcvad = _optional_import("webrtcvad")
    if not webrtcvad:
        return TrimResult(applied=False, method="none", output_path=input_path, error="webrtcvad not available")

    try:
        pcm = _decode_to_pcm16_mono_16k(input_path)
    except Exception as e:  # noqa: BLE001
        return TrimResult(applied=False, method="none", output_path=input_path, error=f"decode failed: {e!s}")

    sample_rate = 16000
    frame_ms = 30
    bytes_per_sample = 2
    frame_bytes = int(sample_rate * (frame_ms / 1000.0) * bytes_per_sample)

    if len(pcm) < frame_bytes:
        return TrimResult(applied=False, method="none", output_path=input_path, error="audio too short to trim")

    vad = webrtcvad.Vad(2)

    speech_flags: list[bool] = []
    frames: list[bytes] = []
    for i in range(0, len(pcm) - frame_bytes + 1, frame_bytes):
        frame = pcm[i : i + frame_bytes]
        frames.append(frame)
        with contextlib.suppress(Exception):
            speech_flags.append(bool(vad.is_speech(frame, sample_rate)))
        if len(speech_flags) < len(frames):
            speech_flags.append(False)

    # Expand speech regions with padding
    pad = 3  # ~90ms
    keep = [False] * len(speech_flags)
    for idx, is_speech in enumerate(speech_flags):
        if not is_speech:
            continue
        start = max(0, idx - pad)
        end = min(len(keep), idx + pad + 1)
        for j in range(start, end):
            keep[j] = True

    if not any(keep):
        return TrimResult(applied=False, method="none", output_path=input_path, error="no speech detected")

    trimmed_pcm = b"".join(frame for frame, k in zip(frames, keep) if k)

    # If trimming removes very little, skip (avoid re-encoding for no gain)
    if len(trimmed_pcm) > 0.9 * len(frames) * frame_bytes:
        return TrimResult(applied=False, method="none", output_path=input_path, error="trim gain too small")

    out_fd, out_path = tempfile.mkstemp(prefix="transcriptturbo_trimmed_", suffix=".wav")
    Path(out_path).unlink(missing_ok=True)
    # close fd from mkstemp; wave will create
    with contextlib.suppress(Exception):
        import os

        os.close(out_fd)

    try:
        _write_wav_pcm16(out_path, pcm16=trimmed_pcm, sample_rate=sample_rate, channels=1)
    except Exception as e:  # noqa: BLE001
        return TrimResult(applied=False, method="none", output_path=input_path, error=f"wav write failed: {e!s}")

    return TrimResult(applied=True, method="backend_vad", output_path=out_path)

