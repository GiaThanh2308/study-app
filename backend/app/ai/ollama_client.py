"""
Kết nối tới Ollama đang chạy local (mặc định http://localhost:11434).
Ollama phải được cài và chạy nền sẵn trên máy (sau khi cài, nó tự chạy nền,
không cần mở terminal riêng để "bật" nó).
"""
import httpx
import json
from typing import AsyncGenerator

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:7b"  # đổi tên model ở đây nếu bạn pull model khác


async def chat_stream(messages: list[dict], model: str = DEFAULT_MODEL) -> AsyncGenerator[str, None]:
    """
    Gửi hội thoại tới Ollama, trả về từng đoạn text khi model sinh ra (streaming).
    messages format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as response:
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break


async def check_ollama_available() -> bool:
    """Kiểm tra Ollama có đang chạy không, dùng cho endpoint health-check."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
