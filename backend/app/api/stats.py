"""API thống kê tổng quan."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.core.database import get_db
from app.models import models, schemas

logger = logging.getLogger("studyapp.stats")
router = APIRouter()


@router.get("/stats/overview", response_model=schemas.OverallStats)
def overview_stats(db: Session = Depends(get_db)):
    """Thống kê tổng quan toàn bộ ứng dụng."""

    total_subjects = db.query(models.Subject).count()
    total_chapters = db.query(models.Chapter).count()
    total_lessons = db.query(models.Lesson).count()
    total_videos = db.query(models.Video).count()
    total_documents = db.query(models.Document).count()
    total_exams = db.query(models.Exam).count()
    total_attempts = db.query(models.ExamAttempt).count()
    completed_attempts = (
        db.query(models.ExamAttempt)
        .filter(models.ExamAttempt.status == "completed")
        .count()
    )

    # Điểm trung bình tổng
    avg_score_row = (
        db.query(sqlfunc.avg(models.ExamAttempt.score))
        .filter(models.ExamAttempt.status == "completed")
        .scalar()
    )
    overall_avg = round(avg_score_row, 2) if avg_score_row is not None else None

    # Stats theo từng môn
    subjects_stats = []
    for subject in db.query(models.Subject).all():
        sub_exams = db.query(models.Exam).filter(models.Exam.subject_id == subject.id).count()

        # Đề đã hoàn thành
        completed_exam_ids = (
            db.query(models.ExamAttempt.exam_id)
            .join(models.Exam)
            .filter(
                models.Exam.subject_id == subject.id,
                models.ExamAttempt.status == "completed",
            )
            .distinct()
            .all()
        )
        completed_exams = len(completed_exam_ids)

        # Điểm trung bình + cao nhất
        attempts_q = (
            db.query(models.ExamAttempt)
            .join(models.Exam)
            .filter(
                models.Exam.subject_id == subject.id,
                models.ExamAttempt.status == "completed",
            )
        )

        avg_score = attempts_q.with_entities(sqlfunc.avg(models.ExamAttempt.score)).scalar()
        best_score = attempts_q.with_entities(sqlfunc.max(models.ExamAttempt.score)).scalar()

        # Tổng câu đã làm + đúng
        totals = (
            attempts_q.with_entities(
                sqlfunc.sum(models.ExamAttempt.total_questions),
                sqlfunc.sum(models.ExamAttempt.total_correct),
            ).first()
        )
        total_q_done = totals[0] or 0
        total_correct = totals[1] or 0
        accuracy = round(total_correct / total_q_done * 100, 1) if total_q_done > 0 else None

        subjects_stats.append(schemas.SubjectStats(
            subject_id=subject.id,
            subject_name=subject.name,
            total_exams=sub_exams,
            completed_exams=completed_exams,
            remaining_exams=sub_exams - completed_exams,
            average_score=round(avg_score, 2) if avg_score is not None else None,
            best_score=round(best_score, 2) if best_score is not None else None,
            total_questions_done=int(total_q_done),
            total_correct=int(total_correct),
            accuracy_percent=accuracy,
        ))

    return schemas.OverallStats(
        total_subjects=total_subjects,
        total_chapters=total_chapters,
        total_lessons=total_lessons,
        total_videos=total_videos,
        total_documents=total_documents,
        total_exams=total_exams,
        total_attempts=total_attempts,
        completed_attempts=completed_attempts,
        overall_average_score=overall_avg,
        subjects=subjects_stats,
    )


@router.get("/stats/mistakes")
def mistake_stats(subject_id: int | None = None, db: Session = Depends(get_db)):
    """
    Sổ lỗi sai: lấy tất cả câu trả lời sai kèm giải thích.
    """
    q = (
        db.query(models.UserAnswer)
        .join(models.ExamAttempt)
        .join(models.ExamQuestion, models.UserAnswer.question_id == models.ExamQuestion.id)
        .join(models.Exam, models.ExamAttempt.exam_id == models.Exam.id)
        .filter(models.UserAnswer.is_correct == False)  # noqa: E712
    )

    if subject_id is not None:
        q = q.filter(models.Exam.subject_id == subject_id)

    wrong_answers = q.order_by(models.ExamAttempt.finished_at.desc()).all()

    results = []
    for wa in wrong_answers:
        question = db.get(models.ExamQuestion, wa.question_id)
        attempt = db.get(models.ExamAttempt, wa.attempt_id)
        exam = db.get(models.Exam, attempt.exam_id) if attempt else None
        subject = db.get(models.Subject, exam.subject_id) if exam else None

        results.append({
            "answer_id": wa.id,
            "attempt_id": wa.attempt_id,
            "exam_title": exam.title if exam else None,
            "subject_name": subject.name if subject else None,
            "question_number": question.question_number if question else None,
            "question_text": question.question_text if question else None,
            "option_a": question.option_a if question else None,
            "option_b": question.option_b if question else None,
            "option_c": question.option_c if question else None,
            "option_d": question.option_d if question else None,
            "selected_answer": wa.selected_answer,
            "correct_answer": question.correct_answer if question else None,
            "explanation": question.explanation if question else None,
            "topic_tag": question.topic_tag if question else None,
        })

    return results
