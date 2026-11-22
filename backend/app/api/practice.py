"""Safe practice attempts, deterministic scoring, mistakes, and progress stats."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.models.domain import (
    Answer,
    Exam,
    ExamAttempt,
    ExamQuestionLink,
    Mistake,
    Question,
    Subject,
    Topic,
)


router = APIRouter()


class SubmittedAnswer(BaseModel):
    question_id: int
    response: Any = None


class SubmitRequest(BaseModel):
    answers: list[SubmittedAnswer] = Field(default_factory=list)


def _answer_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("choice", "value", "answer", "correct_answer"):
            if key in value:
                return value[key]
    return value


def _tf_value(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"t", "true", "1", "đ", "đúng", "yes"}:
        return True
    if normalized in {"f", "false", "0", "s", "sai", "no"}:
        return False
    if normalized in {"", "_", "-", "null", "none"}:
        return None
    raise HTTPException(status_code=422, detail="Đáp án đúng/sai chỉ nhận Đúng, Sai hoặc để trống.")


def _tf_items(value: Any) -> list[bool | None]:
    value = _answer_value(value)
    if isinstance(value, dict):
        value = [value.get(key) for key in ("a", "b", "c", "d")]
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise HTTPException(status_code=422, detail="Câu đúng/sai cần đúng 4 lựa chọn a, b, c, d.")
    return [_tf_value(item) for item in value]


def _short_matches(response: Any, expected: Any) -> bool:
    response = _answer_value(response)
    if response is None or expected is None:
        return False
    user_text = " ".join(str(response).strip().replace(",", ".").split())
    accepted_values = expected.get("accepted", []) if isinstance(expected, dict) else [_answer_value(expected)]
    tolerance_value = expected.get("tolerance", "0") if isinstance(expected, dict) else "0"
    if not isinstance(accepted_values, (list, tuple, set)):
        accepted_values = [accepted_values]
    if not accepted_values:
        return False
    try:
        user_number = Decimal(user_text)
        tolerance = Decimal(str(tolerance_value))
        if not user_number.is_finite() or not tolerance.is_finite() or tolerance < 0:
            return False
    except InvalidOperation:
        user_number = None
        tolerance = None
    if user_number is not None and tolerance is not None:
        for value in accepted_values:
            try:
                expected_number = Decimal(str(value).strip().replace(",", "."))
            except InvalidOperation:
                continue
            if expected_number.is_finite() and abs(user_number - expected_number) <= tolerance:
                return True
        return False
    expected_text = [" ".join(str(value).strip().split()) for value in accepted_values]
    return user_text.casefold() in {value.casefold() for value in expected_text}


def _score_question(question: Question, response: Any, link: ExamQuestionLink, scoring: dict) -> tuple[bool, float, Any, Any]:
    expected = _answer_value(question.answer)
    max_points = float(link.points if link.points is not None else 1.0)

    if question.question_type == "multiple_choice":
        normalized = str(response).strip().upper() if response is not None else ""
        expected_text = str(expected).strip().upper() if expected is not None else ""
        correct = bool(normalized) and normalized == expected_text
        return correct, max_points if correct else 0.0, normalized or None, expected

    if question.question_type == "true_false":
        user_items = _tf_items(response if response is not None else [None] * 4)
        correct_items = _tf_items(expected)
        correct_count = sum(
            1 for user_item, correct_item in zip(user_items, correct_items)
            if user_item is not None and user_item == correct_item
        )
        full_correct = correct_count == 4
        score_map = scoring.get("true_false_correct_items", {"1": 0.1, "2": 0.25, "3": 0.5, "4": 1.0})
        points = float(score_map.get(str(correct_count), 0.0))
        if max_points != 1.0:
            points *= max_points
        normalized = ["T" if item is True else "F" if item is False else None for item in user_items]
        expected_output = ["T" if item is True else "F" for item in correct_items]
        return full_correct, min(points, max_points), normalized, expected_output

    if question.question_type == "short_answer":
        correct = _short_matches(response, expected)
        normalized = None if response is None else str(response).strip()
        return correct, max_points if correct else 0.0, normalized, expected

    raise HTTPException(status_code=409, detail=f"Loại câu hỏi chưa được hỗ trợ chấm tự động: {question.question_type}.")


def _attempt_payload(attempt: ExamAttempt, db: Session) -> dict:
    exam = db.scalar(select(Exam).options(joinedload(Exam.subject)).where(Exam.id == attempt.exam_id))
    payload = {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "finished_at": attempt.finished_at,
        "score": attempt.score,
        "max_score": exam.max_score if exam else 10.0,
        "total_correct": attempt.total_correct,
        "total_questions": attempt.total_questions,
        "exam": {
            "id": exam.id,
            "title": exam.title,
            "subject_name": exam.subject.name,
            "duration_minutes": exam.duration_minutes,
        } if exam else None,
        "results": [],
    }
    if attempt.status != "completed":
        return payload

    answer_rows = db.scalars(
        select(Answer)
        .where(Answer.attempt_id == attempt.id)
        .options(joinedload(Answer.question).joinedload(Question.topic))
        .order_by(Answer.id)
    ).all()
    links_by_question = {
        link.question_id: link
        for link in db.scalars(
            select(ExamQuestionLink).where(ExamQuestionLink.exam_id == attempt.exam_id)
        ).all()
    }
    payload["results"] = [
        {
            "question_id": answer.question_id,
            "position": links_by_question[answer.question_id].position,
            "response": answer.response,
            "expected_answer": answer.question.answer,
            "is_correct": answer.is_correct,
            "score_earned": answer.score_earned,
            "max_points": links_by_question[answer.question_id].points,
            "explanation": answer.question.explanation,
            "topic": answer.question.topic.name if answer.question.topic else None,
        }
        for answer in answer_rows
    ]
    return payload


@router.post("/exams/{exam_id}/start")
def start_attempt(exam_id: int, db: Session = Depends(get_db)):
    exam = db.scalar(
        select(Exam)
        .where(Exam.id == exam_id, Exam.status == "published")
        .options(selectinload(Exam.questions).joinedload(ExamQuestionLink.question))
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề đã xuất bản.")
    if not exam.questions:
        raise HTTPException(status_code=409, detail="Đề chưa có câu hỏi, chưa thể bắt đầu làm.")
    unsupported = [
        link.position
        for link in exam.questions
        if link.question.answer_status != "verified"
        or link.question.answer is None
        or link.question.question_type not in {"multiple_choice", "true_false", "short_answer"}
    ]
    if unsupported:
        raise HTTPException(
            status_code=409,
            detail=f"Đề có câu chưa xác minh đáp án hoặc chưa hỗ trợ chấm tự động: {unsupported}. Đề chỉ được xem, chưa thể làm có chấm điểm.",
        )
    attempt = ExamAttempt(
        exam_id=exam.id,
        status="in_progress",
        total_questions=len(exam.questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return {"id": attempt.id, "exam_id": exam.id, "started_at": attempt.started_at, "status": attempt.status}


@router.get("/attempts/{attempt_id}")
def get_attempt(attempt_id: int, exam_id: int | None = None, db: Session = Depends(get_db)):
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None or (exam_id is not None and attempt.exam_id != exam_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt làm bài.")
    return _attempt_payload(attempt, db)


@router.post("/attempts/{attempt_id}/submit")
def submit_attempt(attempt_id: int, payload: SubmitRequest, db: Session = Depends(get_db)):
    attempt = db.scalar(
        select(ExamAttempt)
        .where(ExamAttempt.id == attempt_id)
        .options(joinedload(ExamAttempt.exam))
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt làm bài.")
    if attempt.status == "completed":
        return _attempt_payload(attempt, db)
    if attempt.status != "in_progress":
        raise HTTPException(status_code=409, detail="Lượt làm bài không ở trạng thái có thể nộp.")

    links = db.scalars(
        select(ExamQuestionLink)
        .where(ExamQuestionLink.exam_id == attempt.exam_id)
        .options(joinedload(ExamQuestionLink.question))
        .order_by(ExamQuestionLink.position)
    ).all()
    link_by_question = {link.question_id: link for link in links}
    submitted = {item.question_id: item.response for item in payload.answers}
    if len(submitted) != len(payload.answers):
        raise HTTPException(status_code=422, detail="Có câu hỏi bị gửi lặp trong bài nộp.")
    unknown_ids = set(submitted) - set(link_by_question)
    if unknown_ids:
        raise HTTPException(status_code=422, detail="Bài nộp chứa câu hỏi không thuộc đề thi này.")

    score_total = 0.0
    total_correct = 0
    for link in links:
        question = link.question
        if question.answer_status != "verified" or question.answer is None:
            raise HTTPException(status_code=409, detail="Đề có đáp án chưa xác minh; không thể chấm điểm.")
        response = submitted.get(question.id)
        is_correct, score_earned, normalized_response, _ = _score_question(
            question,
            response,
            link,
            attempt.exam.scoring_config or {},
        )
        score_total += score_earned
        total_correct += int(is_correct)
        db.add(
            Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                response=normalized_response,
                is_correct=is_correct,
                score_earned=score_earned,
            )
        )
        if not is_correct:
            db.add(Mistake(attempt_id=attempt.id, question_id=question.id))

    attempt.score = round(min(score_total, attempt.exam.max_score), 2)
    attempt.total_correct = total_correct
    attempt.total_questions = len(links)
    attempt.status = "completed"
    attempt.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attempt)
    return _attempt_payload(attempt, db)


@router.get("/stats/overview")
def progress_overview(db: Session = Depends(get_db)):
    subjects = db.scalars(select(Subject).order_by(Subject.id)).all()
    total_attempts = db.scalar(select(func.count()).select_from(ExamAttempt)) or 0
    completed_attempts = db.scalar(
        select(func.count()).select_from(ExamAttempt).where(ExamAttempt.status == "completed")
    ) or 0
    average = db.scalar(select(func.avg(ExamAttempt.score)).where(ExamAttempt.status == "completed"))
    total_exams = db.scalar(select(func.count()).select_from(Exam).where(Exam.status == "published")) or 0
    subject_stats = []
    for subject in subjects:
        exam_count = db.scalar(
            select(func.count()).select_from(Exam).where(Exam.subject_id == subject.id, Exam.status == "published")
        ) or 0
        completed = db.scalar(
            select(func.count())
            .select_from(ExamAttempt)
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(Exam.subject_id == subject.id, ExamAttempt.status == "completed")
        ) or 0
        avg_score = db.scalar(
            select(func.avg(ExamAttempt.score))
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(Exam.subject_id == subject.id, ExamAttempt.status == "completed")
        )
        best_score = db.scalar(
            select(func.max(ExamAttempt.score))
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(Exam.subject_id == subject.id, ExamAttempt.status == "completed")
        )
        questions_done = db.scalar(
            select(func.coalesce(func.sum(ExamAttempt.total_questions), 0))
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(Exam.subject_id == subject.id, ExamAttempt.status == "completed")
        ) or 0
        correct = db.scalar(
            select(func.coalesce(func.sum(ExamAttempt.total_correct), 0))
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(Exam.subject_id == subject.id, ExamAttempt.status == "completed")
        ) or 0
        subject_stats.append(
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_icon": subject.icon,
                "total_exams": exam_count,
                "completed_exams": completed,
                "average_score": round(avg_score, 2) if avg_score is not None else None,
                "best_score": round(best_score, 2) if best_score is not None else None,
                "total_questions_done": int(questions_done),
                "total_correct": int(correct),
                "accuracy_percent": round(correct * 100 / questions_done, 1) if questions_done else None,
            }
        )

    return {
        "total_subjects": len(subjects),
        "total_topics": db.scalar(select(func.count()).select_from(Topic)) or 0,
        "total_exams": total_exams,
        "total_attempts": total_attempts,
        "completed_attempts": completed_attempts,
        "overall_average_score": round(average, 2) if average is not None else None,
        "subjects": subject_stats,
    }


@router.get("/stats/mistakes")
def list_mistakes(subject_id: int | None = None, limit: int = 100, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 250)
    statement = (
        select(Mistake, Question, Exam, Subject, Answer, ExamQuestionLink)
        .join(Question, Question.id == Mistake.question_id)
        .join(Answer, (Answer.attempt_id == Mistake.attempt_id) & (Answer.question_id == Mistake.question_id))
        .join(ExamAttempt, ExamAttempt.id == Mistake.attempt_id)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .join(Subject, Subject.id == Exam.subject_id)
        .join(ExamQuestionLink, (ExamQuestionLink.exam_id == Exam.id) & (ExamQuestionLink.question_id == Question.id))
        .order_by(Mistake.created_at.desc(), Mistake.id.desc())
        .limit(limit)
    )
    if subject_id is not None:
        statement = statement.where(Exam.subject_id == subject_id)
    rows = db.execute(statement).all()
    return [
        {
            "id": mistake.id,
            "attempt_id": mistake.attempt_id,
            "question_id": question.id,
            "question_number": link.position,
            "question_type": question.question_type,
            "question_text": question.content,
            "options": question.options,
            "selected_answer": answer.response,
            "correct_answer": question.answer,
            "explanation": question.explanation,
            "topic_tag": question.topic.name if question.topic else None,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "exam_title": exam.title,
            "score_earned": answer.score_earned,
            "max_points": link.points,
            "created_at": mistake.created_at,
        }
        for mistake, question, exam, subject, answer, link in rows
    ]
