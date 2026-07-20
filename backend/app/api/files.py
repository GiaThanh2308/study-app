import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, DATA_DIR
from app.models import models, schemas

router = APIRouter()

ALLOWED_VIDEO = {".mp4", ".mkv", ".avi", ".mov"}
ALLOWED_DOC = {".pdf"}
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


@router.post("/upload/video", response_model=schemas.VideoOut)
def upload_video(
    lesson_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO:
        raise HTTPException(400, f"Định dạng video không hỗ trợ: {ext}")

    lesson = db.query(models.Lesson).get(lesson_id)
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
        raise HTTPException(400, f"Định dạng tài liệu không hỗ trợ: {ext}")

    subfolder = "exams" if doc_type == "exam" else "pdfs"
    rel_path = _save_upload(file, subfolder)
    doc = models.Document(
        lesson_id=lesson_id,
        subject_id=subject_id,
        doc_type=doc_type,
        file_path=rel_path,
        original_filename=file.filename,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
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

    video = db.query(models.Video).get(video_id)
    if not video:
        raise HTTPException(404, "Video không tồn tại")

    rel_path = _save_upload(file, "transcripts")
    with open(os.path.join(DATA_DIR, rel_path), "r", encoding="utf-8", errors="ignore") as f:
        text_content = f.read()

    transcript = models.Transcript(video_id=video_id, file_path=rel_path, text=text_content)
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return {"id": transcript.id, "video_id": video_id, "file_path": rel_path}
