"""/pronunciation — OpenPronounce English assessment (self-hosted, no Azure).

Routes:
    GET  /pronunciation/health
    POST /pronunciation/assess   multipart: file + expected_text + lang
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pronunciation"], dependencies=[Depends(require_api_key)])

_lock = threading.Lock()
_engine_ready = False
_engine_error: str | None = None


class PronunciationWordOut(BaseModel):
    word: str
    accuracy_score: float = 0.0
    error_type: str = "None"
    expected_ipa: str = ""
    actual_ipa: str = ""
    confidence: float = 0.0


class PronunciationAssessOut(BaseModel):
    score: float
    recognized_text: str = ""
    pronunciation_score: float = 0.0
    accuracy_score: float = 0.0
    fluency_score: float = 0.0
    completeness_score: float = 0.0
    phoneme_error_rate: float = 0.0
    word_error_rate: float = 0.0
    words: list[PronunciationWordOut] = Field(default_factory=list)
    engine: str = "openpronounce"


class PronunciationHealthOut(BaseModel):
    enabled: bool
    ready: bool
    detail: str = ""
    default_lang: str = "en"


def _try_import() -> tuple[bool, str]:
    try:
        import openpronounce  # noqa: F401

        return True, f"openpronounce {getattr(openpronounce, '__version__', '')}".strip()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _ensure_engine() -> None:
    global _engine_ready, _engine_error
    with _lock:
        if _engine_ready or _engine_error:
            return
        ok, detail = _try_import()
        if not ok:
            _engine_error = detail
            return
        # Warm-import heavy modules once (models download on first assess).
        try:
            from openpronounce import compare_audio_with_text, load_audio  # noqa: F401

            _engine_ready = True
            _engine_error = None
        except Exception as exc:  # noqa: BLE001
            _engine_error = str(exc)


def _lang_code(raw: str | None) -> str:
    value = (raw or "en").strip().lower()
    if value.startswith("en"):
        return "en"
    if value.startswith("zh"):
        # OpenPronounce is English-first; reject zh so the app can fall back later.
        raise HTTPException(
            status_code=400,
            detail="OpenPronounce on this server is English-only. Use lang=en.",
        )
    return value[:8] or "en"


def _map_result(raw: dict) -> PronunciationAssessOut:
    score = float(raw.get("score") or 0.0)
    diffs = raw.get("differences") or {}
    if not isinstance(diffs, dict):
        diffs = {}
    per = float(diffs.get("phoneme_error_rate") or 0.0)
    wer = float(diffs.get("word_error_rate") or 0.0)
    accuracy = max(0.0, min(100.0, (1.0 - per) * 100.0))
    completeness = max(0.0, min(100.0, (1.0 - wer) * 100.0))
    # No separate fluency from OpenPronounce core — mirror score.
    fluency = score

    words: list[PronunciationWordOut] = []
    errors = diffs.get("errors") or []
    if isinstance(errors, list):
        for err in errors:
            if not isinstance(err, dict):
                continue
            conf = float(err.get("confidence") or 0.0)
            words.append(
                PronunciationWordOut(
                    word=str(err.get("word") or ""),
                    accuracy_score=max(0.0, min(100.0, (1.0 - conf) * 100.0)),
                    error_type="Mispronunciation",
                    expected_ipa=str(err.get("expected") or ""),
                    actual_ipa=str(err.get("actual") or ""),
                    confidence=conf,
                )
            )

    transcript = str(raw.get("transcribe") or raw.get("transcript") or "")
    return PronunciationAssessOut(
        score=score,
        recognized_text=transcript,
        pronunciation_score=score,
        accuracy_score=accuracy,
        fluency_score=fluency,
        completeness_score=completeness,
        phoneme_error_rate=per,
        word_error_rate=wer,
        words=words,
        engine="openpronounce",
    )


@router.get("/pronunciation/health", response_model=PronunciationHealthOut)
def pronunciation_health() -> PronunciationHealthOut:
    enabled_flag = os.getenv("ENABLE_OPENPRONOUNCE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    if not enabled_flag:
        return PronunciationHealthOut(
            enabled=False,
            ready=False,
            detail="ENABLE_OPENPRONOUNCE is off",
        )
    ok, detail = _try_import()
    return PronunciationHealthOut(
        enabled=ok,
        ready=ok and _engine_ready,
        detail=detail if ok else f"not installed: {detail}",
    )


@router.post("/pronunciation/assess", response_model=PronunciationAssessOut)
async def assess_pronunciation(
    file: UploadFile = File(..., description="Audio recording (wav/m4a/mp3)"),
    expected_text: str = Form(..., description="Reference sentence the user should read"),
    lang: str = Form("en"),
) -> PronunciationAssessOut:
    enabled_flag = os.getenv("ENABLE_OPENPRONOUNCE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    if not enabled_flag:
        raise HTTPException(status_code=503, detail="OpenPronounce is disabled on this server")

    text = expected_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="expected_text is required")
    language = _lang_code(lang)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty audio file")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="audio too large (max 8MB)")

    _ensure_engine()
    if _engine_error and not _engine_ready:
        raise HTTPException(
            status_code=503,
            detail=f"OpenPronounce unavailable: {_engine_error}",
        )

    suffix = Path(file.filename or "recording.wav").suffix or ".wav"
    if len(suffix) > 8:
        suffix = ".wav"

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        from openpronounce import compare_audio_with_text, load_audio

        sound = load_audio(tmp_path)
        # First request downloads ~GB of models — can take minutes on cold start.
        raw = compare_audio_with_text(sound, text, lang=language)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=500, detail="Unexpected OpenPronounce response")
        return _map_result(raw)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("OpenPronounce assess failed")
        raise HTTPException(status_code=500, detail=f"assessment failed: {exc}") from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
