"""
Dùng model vision (moondream - nhẹ, phù hợp máy không GPU) để mô tả
hình ảnh/đồ thị trong trang PDF bằng lời, sau đó gộp mô tả vào text
để RAG có thể "biết" nội dung hình dù bản thân LLM lúc trả lời không thấy ảnh.

Cần chạy: ollama pull moondream
"""
import base64
import httpx
import fitz  # PyMuPDF

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
VISION_MODEL = "moondream"

VISION_PROMPT = (
    "Mô tả ngắn gọn hình ảnh/đồ thị/biểu đồ trong ảnh này bằng tiếng Việt. "
    "Nếu là đồ thị toán/lý, nêu rõ trục, hình dạng đường, các điểm đặc biệt (cực trị, giao điểm...). "
    "Nếu không có hình ảnh/đồ thị nào đáng chú ý (chỉ có chữ), trả lời đúng 1 từ: KHONG_CO_HINH."
)


def page_has_images(page: "fitz.Page") -> bool:
    """Kiểm tra nhanh trang có chứa hình ảnh nhúng không (bỏ qua trang chỉ có chữ)."""
    return len(page.get_images(full=True)) > 0


def render_page_to_base64(page: "fitz.Page", zoom: float = 1.5) -> str:
    """Chụp toàn bộ trang PDF thành ảnh PNG, trả về base64 để gửi cho model vision."""
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")


async def describe_image_base64(image_b64: str) -> str:
    """Gọi model vision qua Ollama, trả về mô tả bằng lời."""
    payload = {
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": VISION_PROMPT, "images": [image_b64]}],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        resp = await client.post(OLLAMA_CHAT_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()


async def describe_pdf_page_if_has_image(pdf_path: str, page_number_zero_based: int) -> str | None:
    """
    Nếu trang có hình, chụp và mô tả. Trả về None nếu trang không có hình
    hoặc model xác nhận không có gì đáng mô tả.
    """
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_number_zero_based]
        if not page_has_images(page):
            return None
        image_b64 = render_page_to_base64(page)
        description = await describe_image_base64(image_b64)
        if "KHONG_CO_HINH" in description.upper().replace(" ", ""):
            return None
        return description
    finally:
        doc.close()
