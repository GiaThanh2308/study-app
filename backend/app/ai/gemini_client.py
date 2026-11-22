"""Gemini Developer API adapter; requests run remotely, never on the local CPU."""

from collections.abc import AsyncIterator
from typing import Any

from app.core.settings import GEMINI_API_KEY, GEMINI_MAX_OUTPUT_TOKENS, GEMINI_MODEL


class GeminiClientError(Exception):
    """Safe, user-facing Gemini configuration or API failure."""


def is_gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)


def _sdk():
    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as exc:
        raise GeminiClientError(
            "Thiếu Google Gen AI SDK. Cài dependencies từ backend/requirements.txt rồi khởi động lại."
        ) from exc
    return genai, errors, types


def _require_key() -> None:
    if not GEMINI_API_KEY:
        raise GeminiClientError(
            "Chưa cấu hình GEMINI_API_KEY trong backend/.env. Chat AI hiện chưa khả dụng."
        )


def _translate_api_error(error: Exception, errors: Any) -> GeminiClientError:
    if isinstance(error, errors.APIError):
        if error.code == 429:
            return GeminiClientError(
                "Gemini đang giới hạn yêu cầu hoặc đã hết quota miễn phí. Hãy thử lại sau khi quota được làm mới."
            )
        if error.code in (401, 403):
            return GeminiClientError("Gemini không chấp nhận API key hoặc project hiện tại không có quyền gọi model.")
    return GeminiClientError("Gemini API hiện không xử lý được yêu cầu. Hãy thử lại sau.")


def _chat_contents(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for message in messages:
        text = (message.get("content") or "").strip()
        if not text:
            continue
        role = "model" if message.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


async def chat_stream(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """Stream a bounded chat response from the configured Gemini model."""
    _require_key()
    genai, errors, types = _sdk()
    contents = _chat_contents(messages)
    if not contents:
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        async with client.aio as async_client:
            stream = await async_client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                    temperature=0.3,
                ),
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
    except Exception as exc:
        raise _translate_api_error(exc, errors) from exc


async def generate_text(contents: list[Any], *, max_output_tokens: int | None = None) -> str:
    """Generate one non-streaming text response for a multimodal request."""
    _require_key()
    genai, errors, types = _sdk()
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        async with client.aio as async_client:
            response = await async_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens or GEMINI_MAX_OUTPUT_TOKENS,
                    temperature=0.1,
                ),
            )
    except Exception as exc:
        raise _translate_api_error(exc, errors) from exc
    return response.text or ""


async def generate_structured(contents: list[Any], response_schema: Any, *, max_output_tokens: int) -> Any:
    """Generate one structured response; reject blocked, empty, or truncated output."""
    _require_key()
    genai, errors, types = _sdk()
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        async with client.aio as async_client:
            response = await async_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=0.2,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
    except Exception as exc:
        raise _translate_api_error(exc, errors) from exc
    candidates = getattr(response, "candidates", None) or []
    if not candidates or str(getattr(candidates[0], "finish_reason", "STOP")).upper().split(".")[-1] not in {"STOP", "FINISHREASON.STOP"}:
        raise GeminiClientError("Gemini trả kết quả chưa hoàn chỉnh; phần này chưa được lưu. Bạn có thể yêu cầu chạy lại thủ công.")
    parsed = getattr(response, "parsed", None)
    if parsed is None:
        raise GeminiClientError("Gemini không trả JSON theo schema yêu cầu; phần này chưa được lưu.")
    return parsed


async def extract_text_from_image(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """Send one user-provided image to Gemini without loading or retaining it locally."""
    _require_key()
    genai, errors, types = _sdk()
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
    ]
    try:
        async with client.aio as async_client:
            response = await async_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                    temperature=0.1,
                ),
            )
    except Exception as exc:
        raise _translate_api_error(exc, errors) from exc
    return response.text or ""
