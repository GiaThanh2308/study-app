import os
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
import fitz  # PyMuPDF

from app.core.database import get_db, DATA_DIR, SessionLocal
from app.models import models
from app.ai.rag.chunking import chunk_pdf
from app.ai.rag.docx_reader import chunk_docx
from app.ai.rag.embeddings import get_embeddings_batch, get_embedding
from app.ai.rag.vector_store import add_chunks, query as vector_query, delete_document
from app.ai.ollama_client import chat_stream

router = APIRouter()

# Theo dõi tiến độ xử lý trong bộ nhớ (đủ dùng cho app chạy 1 tiến trình, local, 1 người dùng).
# Key: document_id -> {"current": int, "total": int, "started_at": float}
_progress_tracker: dict[int, dict] = {}


async def _process_document_task(document_id: int):
    """Chạy nền: đọc PDF -> chunk -> embedding -> lưu vector store."""
    db = SessionLocal()
    try:
        doc = db.query(models.Document).get(document_id)
        if not doc:
            return
        doc.rag_status = "processing"
        db.commit()

        _progress_tracker[document_id] = {
            "current": 0,
            "total": 0,
            "started_at": time.time(),
        }

        def on_page_progress(current_page: int, total_pages: int):
            _progress_tracker[document_id]["current"] = current_page
            _progress_tracker[document_id]["total"] = total_pages

        full_path = os.path.join(DATA_DIR, doc.file_path)
        ext = os.path.splitext(doc.file_path)[1].lower()

        if ext == ".docx":
            chunks = chunk_docx(full_path, progress_callback=on_page_progress)
            content_type = "docx"
        else:
            chunks = await chunk_pdf(full_path, describe_images=True, progress_callback=on_page_progress)
            content_type = "pdf"

        if not chunks:
            doc.rag_status = "error"
            db.commit()
            return

        texts = [c["text"] for c in chunks]
        embeddings = await get_embeddings_batch(texts)
        add_chunks(document_id, doc.original_filename or "tài liệu", chunks, embeddings, content_type=content_type)

        doc.rag_status = "ready"
        doc.page_count = max(c["page"] for c in chunks)
        db.commit()
    except Exception as e:
        import traceback
        print(f"[RAG ERROR] Xử lý document {document_id} thất bại:")
        traceback.print_exc()
        doc = db.query(models.Document).get(document_id)
        if doc:
            doc.rag_status = "error"
            db.commit()
    finally:
        _progress_tracker.pop(document_id, None)
        db.close()


@router.get("/rag/page-image")
def get_page_image(document_id: int, page: int, db: Session = Depends(get_db)):
    """
    Chụp lại đúng 1 trang PDF thành ảnh PNG — dùng để hiển thị gọn trong khung chat
    thay vì nhúng cả trình xem PDF đầy đủ (thanh công cụ, thumbnail...) chỉ để xem 1 trang.
    Chỉ áp dụng cho PDF — DOCX không có khái niệm trang thật nên không cần endpoint này.
    """
    doc = db.query(models.Document).get(document_id)
    if not doc:
        raise HTTPException(404, "Tài liệu không tồn tại")

    full_path = os.path.join(DATA_DIR, doc.file_path)
    pdf = fitz.open(full_path)
    try:
        page_index = page - 1  # tham số "page" đếm từ 1, fitz đếm từ 0
        if page_index < 0 or page_index >= len(pdf):
            raise HTTPException(404, f"Trang {page} không tồn tại trong tài liệu này")

        pix = pdf[page_index].get_pixmap(matrix=fitz.Matrix(2, 2))  # zoom x2 cho nét hơn
        img_bytes = pix.tobytes("png")
    finally:
        pdf.close()

    return Response(content=img_bytes, media_type="image/png")


@router.post("/rag/process/{document_id}")
def process_document(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(models.Document).get(document_id)
    if not doc:
        raise HTTPException(404, "Tài liệu không tồn tại")

    ext = os.path.splitext(doc.file_path)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(400, "Chỉ hỗ trợ xử lý RAG cho file PDF hoặc DOCX")

    background_tasks.add_task(_process_document_task, document_id)
    doc.rag_status = "processing"
    db.commit()
    return {"status": "processing_started", "document_id": document_id}


@router.get("/rag/status/{document_id}")
def rag_status(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).get(document_id)
    if not doc:
        raise HTTPException(404, "Tài liệu không tồn tại")

    result = {"document_id": document_id, "status": doc.rag_status}

    progress = _progress_tracker.get(document_id)
    if progress and progress["total"] > 0:
        current = progress["current"]
        total = progress["total"]
        elapsed = time.time() - progress["started_at"]
        percent = round((current / total) * 100)

        # Ước tính thời gian còn lại dựa trên tốc độ trung bình đã xử lý.
        # Trang đầu luôn chậm hơn (model phải "khởi động"), nên ETA sẽ chính xác dần
        # sau khi xử lý được vài trang, không tin tưởng số ETA quá sớm.
        eta_seconds = None
        if current > 0:
            avg_time_per_page = elapsed / current
            remaining_pages = total - current
            eta_seconds = round(avg_time_per_page * remaining_pages)

        result.update({
            "current_page": current,
            "total_pages": total,
            "percent": percent,
            "eta_seconds": eta_seconds,
        })

    return result


@router.get("/rag/documents")
def list_ready_documents(subject_id: int | None = None, db: Session = Depends(get_db)):
    """Danh sách tài liệu đã sẵn sàng để chat cùng, có thể lọc theo môn học."""
    if subject_id:
        from app.api.tutor import _get_subject_source_ids
        document_ids, _ = _get_subject_source_ids(db, subject_id)
        docs = db.query(models.Document).filter(
            models.Document.id.in_(document_ids), models.Document.rag_status == "ready"
        ).all()
    else:
        docs = db.query(models.Document).filter(models.Document.rag_status == "ready").all()
    return [{"id": d.id, "name": d.original_filename} for d in docs]


class RagChatRequest(BaseModel):
    message: str
    document_id: int | None = None  # ưu tiên cao nhất nếu có: chỉ tìm trong đúng 1 tài liệu
    subject_id: int | None = None   # nếu không chọn tài liệu cụ thể: giới hạn tìm trong đúng 1 môn học


@router.post("/rag/chat")
async def rag_chat(payload: RagChatRequest, db: Session = Depends(get_db)):
    query_emb = await get_embedding(payload.message)

    if payload.document_id:
        # Trường hợp cụ thể nhất: đã chọn đúng 1 tài liệu
        hits = vector_query(query_emb, n_results=4, document_id=payload.document_id)
    elif payload.subject_id:
        # Giới hạn tìm kiếm trong đúng các tài liệu/video thuộc môn học đã chọn
        from app.api.tutor import _get_subject_source_ids
        from app.ai.rag.vector_store import query_within_sources
        document_ids, video_ids = _get_subject_source_ids(db, payload.subject_id)
        hits = query_within_sources(query_emb, document_ids=document_ids, video_ids=video_ids, n_results=4)
    else:
        # Không chọn gì cả: tìm trong toàn bộ tài liệu đã xử lý (mọi môn)
        hits = vector_query(query_emb, n_results=4, document_id=None)

    if not hits:
        context_text = "(Không tìm thấy đoạn tài liệu nào liên quan.)"
        sources = []
    else:
        context_parts = []
        for h in hits:
            if h.get("content_type") == "video":
                from app.ai.video.whisper_transcribe import format_timestamp
                ts = format_timestamp(h["start_time"])
                context_parts.append(f"[Nguồn: video {h['source_name']}, phút {ts}]\n{h['text']}")
            elif h.get("content_type") == "docx":
                context_parts.append(f"[Nguồn: {h['source_name']}, phần {h['page']}]\n{h['text']}")
            else:
                context_parts.append(f"[Nguồn: {h['source_name']}, trang {h['page']}]\n{h['text']}")
        context_text = "\n\n".join(context_parts)

        # Tra ra file_path thật để frontend có thể mở/phát đúng vị trí
        doc_ids = {h["document_id"] for h in hits if h.get("content_type") != "video" and h.get("document_id")}
        video_ids = {h["video_id"] for h in hits if h.get("content_type") == "video"}

        docs_map = {
            d.id: d.file_path
            for d in db.query(models.Document).filter(models.Document.id.in_(doc_ids)).all()
        } if doc_ids else {}
        videos_map = {
            v.id: v.file_path
            for v in db.query(models.Video).filter(models.Video.id.in_(video_ids)).all()
        } if video_ids else {}

        sources = []
        for h in hits:
            if h.get("content_type") == "video":
                from app.ai.video.whisper_transcribe import format_timestamp
                sources.append({
                    "type": "video",
                    "source_name": h["source_name"],
                    "timestamp": format_timestamp(h["start_time"]),
                    "start_seconds": h["start_time"],
                    "video_id": h["video_id"],
                    "file_path": videos_map.get(h["video_id"]),
                })
            elif h.get("content_type") == "docx":
                sources.append({
                    "type": "docx",
                    "source_name": h["source_name"],
                    "part": h["page"],  # số thứ tự "Phần", không phải trang thật
                    "document_id": h["document_id"],
                    "file_path": docs_map.get(h["document_id"]),
                    "snippet": h["text"][:500],  # DOCX không xem trước được bằng ảnh, hiện thẳng đoạn text
                })
            else:
                sources.append({
                    "type": "pdf",
                    "source_name": h["source_name"],
                    "page": h["page"],
                    "document_id": h["document_id"],
                    "file_path": docs_map.get(h["document_id"]),
                })

    system_prompt = (
        "Bạn là trợ lý học tập. Trả lời câu hỏi CHỈ dựa trên các đoạn tài liệu được cung cấp dưới đây. "
        "Nếu tài liệu không có thông tin liên quan, hãy nói rõ là không tìm thấy trong tài liệu. "
        "Trả lời bằng tiếng Việt, ngắn gọn, chính xác.\n\n"
        f"TÀI LIỆU:\n{context_text}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.message},
    ]

    async def event_generator():
        # Gửi sources trước dưới dạng dòng đặc biệt để frontend tách ra hiển thị
        import json
        yield f"__SOURCES__{json.dumps(sources, ensure_ascii=False)}__END_SOURCES__"
        async for chunk in chat_stream(messages):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/plain")


@router.delete("/rag/documents/{document_id}")
def remove_document_vectors(document_id: int, db: Session = Depends(get_db)):
    delete_document(document_id)
    doc = db.query(models.Document).get(document_id)
    if doc:
        doc.rag_status = "pending"
        db.commit()
    return {"ok": True}
