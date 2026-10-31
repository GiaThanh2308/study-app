"""
Tạo embedding (vector số học đại diện cho nghĩa của văn bản) qua Ollama.
Dùng model "bge-m3" — cân bằng giữa dung lượng (~1.2GB) và chất lượng đa ngôn ngữ,
đặc biệt phù hợp cho tiếng Việt so với các model embedding nhẹ khác.
Cần chạy: ollama pull bge-m3
"""
import httpx

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "bge-m3"


async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        resp = await client.post(
            OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Ollama chưa hỗ trợ batch thật, nên gọi tuần tự — chấp nhận được vì chạy nền lúc import tài liệu."""
    results = []
    for text in texts:
        emb = await get_embedding(text)
        results.append(emb)
    return results
