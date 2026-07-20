"""
Đọc PDF bằng PyMuPDF (fitz) — trích text theo từng trang, chia nhỏ thành
các đoạn (chunk). Nếu trang có hình/đồ thị, gọi model vision mô tả và
gộp vào text của trang đó trước khi chunk, để RAG "biết" nội dung hình.
"""
import fitz  # PyMuPDF
from app.ai.rag.vision import describe_pdf_page_if_has_image

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


async def extract_pages(pdf_path: str, describe_images: bool = True, progress_callback=None) -> list[dict]:
    """
    Trả về [{"page": 1, "text": "..."}, ...], text đã gộp mô tả hình nếu có.
    progress_callback(current_page, total_pages) được gọi sau mỗi trang xử lý xong.
    """
    doc = fitz.open(pdf_path)
    pages = []
    total = len(doc)
    try:
        if progress_callback:
            progress_callback(0, total)  # báo tổng số trang ngay, trước khi xử lý trang nào

        for i in range(total):
            page = doc[i]
            text = page.get_text() or ""

            if describe_images:
                try:
                    image_desc = await describe_pdf_page_if_has_image(pdf_path, i)
                    if image_desc:
                        text += f"\n\n[Mô tả hình ảnh/đồ thị trong trang]: {image_desc}"
                except Exception:
                    # Nếu model vision lỗi (chưa cài, quá chậm...), vẫn giữ text chữ, không chặn cả quá trình
                    pass

            pages.append({"page": i + 1, "text": text})

            if progress_callback:
                progress_callback(i + 1, total)
    finally:
        doc.close()
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


async def chunk_pdf(pdf_path: str, describe_images: bool = True, progress_callback=None) -> list[dict]:
    """Trả về danh sách chunk kèm số trang: [{"text": "...", "page": 3}, ...]"""
    pages = await extract_pages(pdf_path, describe_images=describe_images, progress_callback=progress_callback)
    all_chunks = []
    for page_data in pages:
        page_chunks = chunk_text(page_data["text"])
        for c in page_chunks:
            if c.strip():
                all_chunks.append({"text": c, "page": page_data["page"]})
    return all_chunks
