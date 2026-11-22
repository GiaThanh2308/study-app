from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models import models, schemas

router = APIRouter()


# ---------- Subjects ----------
@router.get("/subjects", response_model=list[schemas.SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()


@router.post("/subjects", response_model=schemas.SubjectOut)
def create_subject(payload: schemas.SubjectCreate, db: Session = Depends(get_db)):
    subject = models.Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).get(subject_id)
    if not subject:
        raise HTTPException(404, "Không tìm thấy môn học")
    db.delete(subject)
    db.commit()
    return {"ok": True}


# ---------- Chapters ----------
@router.post("/chapters", response_model=schemas.ChapterOut)
def create_chapter(payload: schemas.ChapterCreate, db: Session = Depends(get_db)):
    chapter = models.Chapter(**payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.delete("/chapters/{chapter_id}")
def delete_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(models.Chapter).get(chapter_id)
    if not chapter:
        raise HTTPException(404, "Không tìm thấy chương")
    db.delete(chapter)
    db.commit()
    return {"ok": True}


# ---------- Lessons ----------
@router.post("/lessons", response_model=schemas.LessonOut)
def create_lesson(payload: schemas.LessonCreate, db: Session = Depends(get_db)):
    lesson = models.Lesson(**payload.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(models.Lesson).get(lesson_id)
    if not lesson:
        raise HTTPException(404, "Không tìm thấy bài học")
    db.delete(lesson)
    db.commit()
    return {"ok": True}


# ---------- Cây thư mục đầy đủ: Môn -> Chương -> Bài -> Video/PDF ----------
@router.get("/tree", response_model=list[schemas.SubjectTree])
def get_tree(db: Session = Depends(get_db)):
    subjects = (
        db.query(models.Subject)
        .options(
            joinedload(models.Subject.chapters)
            .joinedload(models.Chapter.lessons)
            .joinedload(models.Lesson.videos),
            joinedload(models.Subject.chapters)
            .joinedload(models.Chapter.lessons)
            .joinedload(models.Lesson.documents),
        )
        .all()
    )
    return subjects
