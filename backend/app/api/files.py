"""Upload file video, PDF, Word, transcript — với hỗ trợ trích xuất text và RAG indexing."""
import os
import shutil
import uuid
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, DATA_DIR
from app.models import models, schemas
from app.ai.rag import index_content

logger = logging.getLogger("studyapp.files")
router = APIRouter()

ALLOWED_VIDEO = {".mp4", ".mkv", ".avi", ".mov"}
ALLOWED_DOC = {".pdf", ".docx", ".doc"}
ALLOWED_SUB = {".srt", ".vtt", ".txt"}


def _save_upload(upload: UploadFile, subfolder: str) -> str:
    """Lưu file vào data/<subfolder>/ với tên duy nhất, trả về đường dẫn tương đối."""
    ext = os.path.splitext(upload.filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    folder = os.path.join(DATA_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, unique_name)
    with open(dest, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return os.path.join(subfolder, unique_name)


def _extract_pdf_text(file_path: str) -> str:
    """Trích xuất text từ file PDF."""
    try:
        from PyPDF2 import PdfReader
        full_path = os.path.join(DATA_DIR, file_path)
        reader = PdfReader(full_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning(f"Không thể trích xuất text PDF {file_path}: {e}")
        return ""


def _extract_docx_text(file_path: str) -> str:
    """Trích xuất text từ file Word (.docx)."""
    try:
        from docx import Document as DocxDocument
        full_path = os.path.join(DATA_DIR, file_path)
        doc = DocxDocument(full_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        # Cũng lấy text từ bảng
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning(f"Không thể trích xuất text DOCX {file_path}: {e}")
        return ""


def _get_metadata_for_lesson(db: Session, lesson_id: int) -> dict:
    """Lấy thông tin môn/chương/bài từ lesson_id."""
    lesson = db.get(models.Lesson, lesson_id)
    if not lesson:
        return {}
    chapter = db.get(models.Chapter, lesson.chapter_id)
    if not chapter:
        return {"lesson_title": lesson.title}
    subject = db.get(models.Subject, chapter.subject_id)
    return {
        "subject_id": chapter.subject_id,
        "chapter_name": chapter.name,
        "lesson_title": lesson.title,
    }


@router.post("/upload/video", response_model=schemas.VideoOut)
def upload_video(
    lesson_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO:
        raise HTTPException(400, f"Định dạng video không hỗ trợ: {ext}")

    lesson = db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Bài học không tồn tại")

    rel_path = _save_upload(file, "videos")
    video = models.Video(
        lesson_id=lesson_id,
        file_path=rel_path,
        original_filename=file.filename,
        status="pending",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    logger.info(f"Upload video #{video.id}: {file.filename}")
    return video


@router.post("/upload/document", response_model=schemas.DocumentOut)
def upload_document(
    lesson_id: int | None = Form(None),
    subject_id: int | None = Form(None),
    doc_type: str = Form("pdf"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC:
        raise HTTPException(400, f"Định dạng tài liệu không hỗ trợ: {ext}. Hỗ trợ: PDF, Word (.docx)")

    # Xác định doc_type từ extension
    if ext in {".docx", ".doc"}:
        actual_doc_type = "docx"
    else:
        actual_doc_type = doc_type  # pdf hoặc exam

    subfolder = "exams" if actual_doc_type == "exam" else "pdfs"
    rel_path = _save_upload(file, subfolder)

    # Trích xuất text
    text_content = ""
    if ext == ".pdf":
        text_content = _extract_pdf_text(rel_path)
    elif ext in {".docx", ".doc"}:
        text_content = _extract_docx_text(rel_path)

    doc = models.Document(
        lesson_id=lesson_id,
        subject_id=subject_id,
        doc_type=actual_doc_type,
        file_path=rel_path,
        original_filename=file.filename,
        text_content=text_content if text_content else None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Index vào kho kiến thức (RAG)
    if text_content:
        metadata = {}
        if lesson_id:
            metadata = _get_metadata_for_lesson(db, lesson_id)
        elif subject_id:
            subject = db.get(models.Subject, subject_id)
            if subject:
                metadata["subject_id"] = subject_id

        index_content(
            db=db,
            content=text_content,
            source_type=actual_doc_type,
            source_id=doc.id,
            **metadata,
        )

    logger.info(f"Upload document #{doc.id}: {file.filename} ({actual_doc_type})")
    return doc


@router.post("/upload/transcript")
def upload_transcript(
    video_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_SUB:
        raise HTTPException(400, f"Định dạng transcript không hỗ trợ: {ext}")

    video = db.get(models.Video, video_id)
    if not video:
        raise HTTPException(404, "Video không tồn tại")

    rel_path = _save_upload(file, "transcripts")
    with open(os.path.join(DATA_DIR, rel_path), "r", encoding="utf-8", errors="ignore") as f:
        text_content = f.read()

    transcript = models.Transcript(video_id=video_id, file_path=rel_path, text=text_content)
    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    # Index transcript vào kho kiến thức (RAG)
    if text_content:
        metadata = _get_metadata_for_lesson(db, video.lesson_id)
        index_content(
            db=db,
            content=text_content,
            source_type="video_transcript",
            source_id=transcript.id,
            video_id=video_id,
            **metadata,
        )

    logger.info(f"Upload transcript #{transcript.id} cho video #{video_id}")
    return {"id": transcript.id, "video_id": video_id, "file_path": rel_path}
