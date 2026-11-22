"""Tavily Search API client restricted to the free Basic Search operation."""

from typing import Any

import httpx
from app.core.settings import TAVILY_API_KEY

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_TIMEOUT_SECONDS = 20.0


class TavilySearchError(Exception):
    """Provider error with a safe message suitable for an API response."""


def _error_message(status_code: int) -> str:
    if status_code in (401, 403):
        return "Tavily không chấp nhận API key. Hãy kiểm tra TAVILY_API_KEY trong backend/.env."
    if status_code in (402, 429, 432, 433):
        return "Tavily đã giới hạn yêu cầu hoặc hết quota miễn phí. Không có yêu cầu trả phí nào được gửi."
    return f"Tavily Search gặp lỗi HTTP {status_code}."


async def search_web(query: str, max_results: int = 10) -> dict[str, Any]:
    """Search the web using Basic depth only; never requests paid plan upgrades."""
    api_key = TAVILY_API_KEY
    if not api_key or api_key == "your_free_tavily_api_key_here":
        raise TavilySearchError(
            "Chưa cấu hình Tavily API key. Tạo key ở gói free và đặt trong backend/.env."
        )

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "topic": "general",
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_usage": True,
    }

    try:
        async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT_SECONDS) as client:
            response = await client.post(
                TAVILY_SEARCH_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise TavilySearchError("Tavily không phản hồi kịp thời. Hãy thử lại sau.") from exc
    except httpx.RequestError as exc:
        raise TavilySearchError("Không kết nối được Tavily. Kiểm tra kết nối mạng rồi thử lại.") from exc

    if response.status_code != 200:
        raise TavilySearchError(_error_message(response.status_code))

    try:
        data = response.json()
    except ValueError as exc:
        raise TavilySearchError("Tavily trả về dữ liệu không đọc được.") from exc

    results = []
    for item in data.get("results", []):
        if not isinstance(item, dict) or not item.get("url"):
            continue
        results.append(
            {
                "title": item.get("title") or "(Không có tiêu đề)",
                "url": item["url"],
                "snippet": item.get("content") or "",
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
        )

    return {
        "provider": "tavily",
        "query": query,
        "search_depth": "basic",
        "credits_used": (data.get("usage") or {}).get("credits"),
        "results": results,
    }
