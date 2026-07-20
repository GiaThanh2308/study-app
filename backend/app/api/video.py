import os
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db, DATA_DIR, SessionLocal
from app.models import models
from app.ai.video.whisper_transcribe import transcribe_video, format_timestamp
from app.ai.video.chunking import chunk_transcript
from app.ai.rag.embeddings import get_embeddings_batch
from app.ai.rag.vector_store import add_video_chunks, delete_video

router = APIRouter()

# Theo dõi tiến độ xử lý video trong bộ nhớ, tương tự cơ chế đã dùng cho PDF.
_video_progress_tracker: dict[int, dict] = {}


def _process_video_task_sync(video_id: int):
    """
    Whisper hiện tại chạy đồng bộ (không hỗ trợ async native), nên hàm này
    chạy trong background task bình thường của FastAPI (chạy trong threadpool).
    """
    db = SessionLocal()
    try:
        video = db.query(models.Video).get(video_id)
        if not video:
            return
        video.rag_status = "processing"
        db.commit()

        _video_progress_tracker[video_id] = {"current": 0, "total": 0, "started_at": time.time()}

        def on_progress(current_seconds, total_seconds):
            _video_progress_tracker[video_id]["current"] = current_seconds
            _video_progress_tracker[video_id]["total"] = total_seconds

        full_path = os.path.join(DATA_DIR, video.file_path)
        segments = transcribe_video(full_path, progress_callback=on_progress)

        if not segments:
            video.rag_status = "error"
            db.commit()
            return

        # Lưu transcript đầy đủ vào bảng Transcript (để xem lại dạng text nếu cần)
        full_text = " ".join(s["text"] for s in segments)
        existing = db.query(models.Transcript).filter(models.Transcript.video_id == video_id).first()
        if existing:
            existing.text = full_text
        else:
            db.add(models.Transcript(video_id=video_id, text=full_text))
        db.commit()

        chunks = chunk_transcript(segments)
        if not chunks:
            video.rag_status = "error"
            db.commit()
            return

        # Embedding chạy async, nhưng hàm này đang sync — chạy trong event loop mới
        import asyncio
        texts = [c["text"] for c in chunks]
        embeddings = asyncio.run(get_embeddings_batch(texts))

        add_video_chunks(video_id, video.original_filename or "video", chunks, embeddings)

        video.rag_status = "ready"
        db.commit()
    except Exception:
        import traceback
        print(f"[VIDEO RAG ERROR] Xử lý video {video_id} thất bại:")
        traceback.print_exc()
        video = db.query(models.Video).get(video_id)
        if video:
            video.rag_status = "error"
            db.commit()
    finally:
        _video_progress_tracker.pop(video_id, None)
        db.close()


@router.post("/video/process/{video_id}")
def process_video(video_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    video = db.query(models.Video).get(video_id)
    if not video:
        raise HTTPException(404, "Video không tồn tại")

    background_tasks.add_task(_process_video_task_sync, video_id)
    video.rag_status = "processing"
    db.commit()
    return {"status": "processing_started", "video_id": video_id}


@router.get("/video/status/{video_id}")
def video_status(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).get(video_id)
    if not video:
        raise HTTPException(404, "Video không tồn tại")

    result = {"video_id": video_id, "status": video.rag_status}

    progress = _video_progress_tracker.get(video_id)
    if progress and progress["total"] > 0:
        current = progress["current"]
        total = progress["total"]
        elapsed = time.time() - progress["started_at"]
        percent = round((current / total) * 100)

        eta_seconds = None
        if current > 0:
            avg_time_per_second_video = elapsed / current
            remaining = total - current
            eta_seconds = round(avg_time_per_second_video * remaining)

        result.update({
            "current_time": format_timestamp(current),
            "total_time": format_timestamp(total),
            "percent": percent,
            "eta_seconds": eta_seconds,
        })

    return result


@router.delete("/video/vectors/{video_id}")
def remove_video_vectors(video_id: int, db: Session = Depends(get_db)):
    delete_video(video_id)
    video = db.query(models.Video).get(video_id)
    if video:
        video.rag_status = "pending"
        db.commit()
    return {"ok": True}
