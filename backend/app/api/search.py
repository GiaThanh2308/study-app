from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import models

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Tìm kiếm text đơn giản trên tên bài học, tên môn, tên file (chưa dùng AI)."""
    like = f"%{q}%"

    lessons = db.query(models.Lesson).filter(models.Lesson.title.ilike(like)).all()
    subjects = db.query(models.Subject).filter(models.Subject.name.ilike(like)).all()
    documents = db.query(models.Document).filter(
        models.Document.original_filename.ilike(like)
    ).all()
    videos = db.query(models.Video).filter(
        models.Video.original_filename.ilike(like)
    ).all()

    return {
        "subjects": [{"id": s.id, "name": s.name} for s in subjects],
        "lessons": [{"id": l.id, "title": l.title, "chapter_id": l.chapter_id} for l in lessons],
        "documents": [{"id": d.id, "name": d.original_filename} for d in documents],
        "videos": [{"id": v.id, "name": v.original_filename} for v in videos],
    }
