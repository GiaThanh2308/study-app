from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine, DATA_DIR
from app.api import structure, files, search, chat, rag, video, practice, flashcards

# Tạo bảng nếu chưa có (Giai đoạn 2 dùng luôn create_all cho đơn giản;
# khi project lớn hơn nên chuyển sang Alembic để quản lý migration)
Base.metadata.create_all(bind=engine)

# Khi backend khởi động lại, mọi tài liệu đang ở trạng thái "processing" chắc chắn
# là dở dang từ lần chạy trước (task nền đã chết theo tiến trình cũ) — reset về "error"
# để người dùng biết và có thể bấm xử lý lại, tránh bị kẹt vĩnh viễn.
def _reset_stale_processing_status():
    from app.core.database import SessionLocal
    from app.models import models as _models
    db = SessionLocal()
    try:
        stale_docs = db.query(_models.Document).filter(_models.Document.rag_status == "processing").all()
        for d in stale_docs:
            d.rag_status = "error"
        stale_videos = db.query(_models.Video).filter(_models.Video.rag_status == "processing").all()
        for v in stale_videos:
            v.rag_status = "error"
        if stale_docs or stale_videos:
            db.commit()
    finally:
        db.close()

_reset_stale_processing_status()

app = FastAPI(title="StudyApp API - Giai đoạn 2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(structure.router, prefix="/api", tags=["structure"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(rag.router, prefix="/api", tags=["rag"])
app.include_router(video.router, prefix="/api", tags=["video"])
app.include_router(practice.router, prefix="/api", tags=["practice"])
app.include_router(flashcards.router, prefix="/api", tags=["flashcards"])

# Cho phép frontend truy cập trực tiếp file (xem PDF, phát video) qua /data/...
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/")
def root():
    return {"status": "ok", "message": "StudyApp backend đang chạy"}
