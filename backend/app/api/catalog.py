"""Deterministic catalog queries for exams already reviewed and published."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.models.domain import Exam, ExamQuestionLink, Question, SourceRecord, Subject, Topic


router = APIRouter()
EXAM_CATEGORIES = {
    "national_previous_year",
    "mock",
    "midterm",
    "final",
    "monthly",
    "reference",
    "generated",
}


def _exam_query(
    *,
    subject_id: int | None,
    category: str | None,
    year_from: int | None,
    year_to: int | None,
    semester: str | None,
    month: int | None,
    province: str | None,
    school: str | None,
    provenance_status: str | None,
    source_kind: str | None,
    topic_id: int | None,
    q: str | None,
):
    statement = select(Exam).where(Exam.status == "published")
    if subject_id is not None:
        statement = statement.where(Exam.subject_id == subject_id)
    if category:
        statement = statement.where(Exam.category == category)
    if year_from is not None:
        statement = statement.where(Exam.exam_year >= year_from)
    if year_to is not None:
        statement = statement.where(Exam.exam_year <= year_to)
    if semester:
        statement = statement.where(Exam.semester == semester)
    if month is not None:
        statement = statement.where(Exam.exam_month == month)
    if province:
        statement = statement.where(Exam.province.ilike(f"%{province.strip()}%"))
    if school:
        statement = statement.where(Exam.school_name.ilike(f"%{school.strip()}%"))
    if provenance_status:
        statement = statement.where(Exam.provenance_status == provenance_status)
    if source_kind:
        statement = statement.where(Exam.sources.any(SourceRecord.source_kind == source_kind))
    if topic_id is not None:
        statement = statement.join(ExamQuestionLink).join(Question).where(Question.topic_id == topic_id)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Exam.title.ilike(needle),
                Exam.questions.any(ExamQuestionLink.question.has(Question.content.ilike(needle))),
            )
        )
    return statement


def _can_practice(exam: Exam) -> bool:
    return bool(exam.questions) and all(
        link.question.answer_status == "verified" and link.question.answer is not None
        for link in exam.questions
    )


def _exam_summary(exam: Exam) -> dict:
    return {
        "id": exam.id,
        "subject_id": exam.subject_id,
        "subject_name": exam.subject.name,
        "subject_icon": exam.subject.icon,
        "title": exam.title,
        "category": exam.category,
        "exam_year": exam.exam_year,
        "semester": exam.semester,
        "exam_month": exam.exam_month,
        "province": exam.province,
        "school_name": exam.school_name,
        "duration_minutes": exam.duration_minutes,
        "total_questions": exam.total_questions,
        "max_score": exam.max_score,
        "provenance_status": exam.provenance_status,
        "source_kinds": sorted({source.source_kind for source in exam.sources}),
        "status": exam.status,
        "can_practice": _can_practice(exam),
    }


@router.get("/catalog/subjects")
def list_catalog_subjects(db: Session = Depends(get_db)):
    subjects = db.scalars(select(Subject).order_by(Subject.id)).all()
    return [
        {
            "id": subject.id,
            "slug": subject.slug,
            "name": subject.name,
            "icon": subject.icon,
            "topics": [
                {"id": topic.id, "name": topic.name, "grade": topic.grade, "code": topic.code}
                for topic in sorted(subject.topics, key=lambda item: (item.grade, item.name))
            ],
        }
        for subject in subjects
    ]


@router.get("/exams")
def list_exams(
    subject_id: int | None = None,
    category: str | None = Query(default=None, max_length=40),
    year_from: int | None = Query(default=None, ge=2000, le=2100),
    year_to: int | None = Query(default=None, ge=2000, le=2100),
    semester: str | None = Query(default=None, max_length=16),
    month: int | None = Query(default=None, ge=1, le=12),
    province: str | None = Query(default=None, max_length=120),
    school: str | None = Query(default=None, max_length=240),
    provenance_status: str | None = Query(default=None, max_length=24),
    source_kind: str | None = Query(default=None, max_length=24),
    topic_id: int | None = None,
    q: str | None = Query(default=None, max_length=300),
    sort: str = Query(default="newest", pattern="^(newest|oldest|year_desc|year_asc)$"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(status_code=422, detail="year_from phải nhỏ hơn hoặc bằng year_to.")
    if category and category not in EXAM_CATEGORIES:
        raise HTTPException(status_code=422, detail="Loại đề không nằm trong danh mục được hỗ trợ.")
    statement = _exam_query(
        subject_id=subject_id,
        category=category,
        year_from=year_from,
        year_to=year_to,
        semester=semester,
        month=month,
        province=province,
        school=school,
        provenance_status=provenance_status,
        source_kind=source_kind,
        topic_id=topic_id,
        q=q,
    )
    filtered_ids = statement.with_only_columns(Exam.id).order_by(None).distinct().subquery()
    count_statement = select(func.count()).select_from(filtered_ids)
    ordering = {
        "newest": (Exam.created_at.desc(), Exam.id.desc()),
        "oldest": (Exam.created_at.asc(), Exam.id.asc()),
        "year_desc": (Exam.exam_year.desc(), Exam.id.desc()),
        "year_asc": (Exam.exam_year.asc(), Exam.id.asc()),
    }[sort]
    statement = (
        statement.distinct()
        .options(
            joinedload(Exam.subject),
            selectinload(Exam.questions).joinedload(ExamQuestionLink.question),
            selectinload(Exam.sources),
        )
        .order_by(*ordering)
        .limit(limit)
        .offset(offset)
    )
    exams = db.scalars(statement).unique().all()
    total = db.scalar(count_statement) or 0
    return {"items": [_exam_summary(exam) for exam in exams], "total": total, "limit": limit, "offset": offset}


@router.get("/exams/{exam_id}")
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.scalar(
        select(Exam)
        .where(Exam.id == exam_id, Exam.status == "published")
        .options(
            joinedload(Exam.subject),
            selectinload(Exam.questions).joinedload(ExamQuestionLink.question).joinedload(Question.topic),
            selectinload(Exam.sources),
        )
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề đã xuất bản.")
    questions = []
    for link in exam.questions:
        question = link.question
        questions.append(
            {
                "id": question.id,
                "position": link.position,
                "section": link.section,
                "question_type": question.question_type,
                "content": question.content,
                "options": question.options,
                "topic": question.topic.name if question.topic else None,
                "max_points": link.points,
                "answer_status": question.answer_status,
            }
        )
    return {
        **_exam_summary(exam),
        "duration_minutes": exam.duration_minutes,
        "questions": questions,
        "sources": [
            {
                "source_kind": source.source_kind,
                "source_url": source.source_url,
                "original_filename": source.original_filename,
                "sha256": source.sha256,
            }
            for source in exam.sources
        ],
    }
