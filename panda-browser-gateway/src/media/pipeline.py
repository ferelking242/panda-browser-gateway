"""
Media pipeline — audio transcription (Whisper) + PDF text extraction.

Audio:
  - MEDIA_BACKEND=hosted → calls MEDIA_MODEL_URL/v1/audio/transcriptions
  - MEDIA_BACKEND=local  → uses faster-whisper locally (CPU, base model)

PDF:
  - Uses pypdf to extract text page by page
  - Falls back to passing raw file to the provider if extraction fails

Entry point: process_attachments(file_paths, image_paths)
  Returns: (remaining_file_paths, image_paths, extra_context_str)
  The extra_context_str is prepended to the prompt automatically.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

log = logging.getLogger("media_pipeline")

# ── Type helpers ─────────────────────────────────────────────────

_AUDIO_EXTS = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".webm", ".opus", ".aac"}
_PDF_EXTS = {".pdf"}


def is_audio_file(path: str) -> bool:
    return Path(path).suffix.lower() in _AUDIO_EXTS


def is_pdf_file(path: str) -> bool:
    return Path(path).suffix.lower() in _PDF_EXTS


# ── Audio transcription ──────────────────────────────────────────

async def transcribe_audio(file_path: str) -> str | None:
    """
    Transcribe an audio file to text.

    Delegates to hosted Whisper API or local faster-whisper depending on
    Config.MEDIA_BACKEND. Returns None on failure (caller decides fallback).
    """
    from src.config import Config

    if Config.MEDIA_BACKEND == "hosted" and Config.MEDIA_MODEL_URL:
        return await _transcribe_via_api(file_path)
    return await _transcribe_local(file_path)


async def _transcribe_via_api(file_path: str) -> str | None:
    """POST audio to a hosted OpenAI-compatible Whisper endpoint."""
    try:
        import httpx
        from src.config import Config

        url = Config.MEDIA_MODEL_URL.rstrip("/") + "/v1/audio/transcriptions"
        headers: dict = {}
        if Config.MEDIA_MODEL_KEY:
            headers["Authorization"] = f"Bearer {Config.MEDIA_MODEL_KEY}"

        async with httpx.AsyncClient(timeout=120) as client:
            with open(file_path, "rb") as f:
                resp = await client.post(
                    url,
                    headers=headers,
                    files={"file": (Path(file_path).name, f, "audio/mpeg")},
                    data={"model": "whisper-1"},
                )
            resp.raise_for_status()
            text = resp.json().get("text", "").strip()
            log.info(f"Whisper API transcribed {Path(file_path).name}: {len(text)} chars")
            return text or None
    except Exception as e:
        log.error(f"Whisper API transcription failed for {file_path}: {e}")
        return None


async def _transcribe_local(file_path: str) -> str | None:
    """Transcribe locally with faster-whisper (CPU, base model)."""
    try:
        # Import check — fail fast with a helpful message
        import faster_whisper  # noqa: F401
    except ImportError:
        log.warning(
            "faster-whisper not installed — audio transcription unavailable. "
            "Run: pip install faster-whisper"
        )
        return None

    try:
        def _run() -> str:
            from faster_whisper import WhisperModel

            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(file_path, beam_size=5)
            return " ".join(seg.text for seg in segments).strip()

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _run)
        log.info(f"Local Whisper transcribed {Path(file_path).name}: {len(text)} chars")
        return text or None
    except Exception as e:
        log.error(f"Local Whisper transcription failed for {file_path}: {e}")
        return None


# ── PDF extraction ───────────────────────────────────────────────

async def extract_pdf_text(file_path: str) -> str | None:
    """
    Extract text from a PDF file using pypdf.

    Returns page-annotated text, or None if extraction fails / empty.
    Falls back to the provider's native PDF upload if None.
    """
    try:
        import pypdf  # noqa: F401
    except ImportError:
        log.warning(
            "pypdf not installed — PDF text extraction unavailable. "
            "Run: pip install pypdf"
        )
        return None

    try:
        def _run() -> str:
            import pypdf

            reader = pypdf.PdfReader(file_path)
            pages: list[str] = []
            for i, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append(f"[Page {i + 1}]\n{text}")
            return "\n\n".join(pages)

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _run)
        if text:
            log.info(
                f"PDF extracted {Path(file_path).name}: "
                f"{len(text)} chars from {text.count('[Page ')} page(s)"
            )
            return text
        log.warning(f"PDF {file_path} yielded no extractable text")
        return None
    except Exception as e:
        log.error(f"PDF extraction failed for {file_path}: {e}")
        return None


# ── Main entry point ─────────────────────────────────────────────

async def process_attachments(
    file_paths: list[str],
    image_paths: list[str],
) -> tuple[list[str], list[str], str]:
    """
    Pre-process all attachments before sending to the provider.

    - Audio files  → transcribed to text (injected as context)
    - PDF files    → text extracted (injected as context) or kept as file
    - Image files  → unchanged (passed directly to client.send_message)
    - Other files  → unchanged (passed directly to client.send_message)

    Returns:
        (remaining_file_paths, image_paths, extra_context)

    extra_context is a formatted string to prepend to the user prompt.
    If empty, nothing is prepended.
    """
    remaining_files: list[str] = []
    extra_parts: list[str] = []

    for fp in file_paths:
        if is_audio_file(fp):
            log.info(f"Media pipeline: transcribing audio {Path(fp).name}")
            text = await transcribe_audio(fp)
            if text:
                extra_parts.append(
                    f"[Audio transcription — {Path(fp).name}]\n{text}"
                )
            else:
                log.warning(f"Audio transcription failed for {fp} — file skipped")

        elif is_pdf_file(fp):
            log.info(f"Media pipeline: extracting PDF {Path(fp).name}")
            text = await extract_pdf_text(fp)
            if text:
                extra_parts.append(
                    f"[Document content — {Path(fp).name}]\n{text}"
                )
            else:
                # pypdf failed or not installed → let the provider handle it natively
                log.info(f"PDF extraction unavailable for {fp} — passing to provider")
                remaining_files.append(fp)

        else:
            remaining_files.append(fp)

    extra_context = "\n\n---\n\n".join(extra_parts)
    if extra_context:
        log.info(
            f"Media pipeline produced {len(extra_parts)} context block(s), "
            f"{len(extra_context)} total chars"
        )

    return remaining_files, image_paths, extra_context
