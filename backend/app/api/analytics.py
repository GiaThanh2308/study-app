from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import models
from app.ai.rag.embeddings import get_embedding
from app.ai.rag.vector_store import query_within_sources
from app.ai.video.whisper_transcribe import format_timestamp
from app.api.tutor import _get_subject_source_ids

router = APIRouter()

SESSION_GAP_MINUTES = 10   # 2 hoạt động cách nhau dưới 10 phút coi là cùng 1 phiên học liên tục
MIN_EVENT_MINUTES = 1      # mỗi hoạt động đơn lẻ (không có hoạt động liền sau) tính tối thiểu 1 phút
DAILY_GOAL_MINUTES = 60    # mục tiêu học mỗi ngày mặc định — có thể chỉnh lại con số này


def _sessionize(timestamps: list, gap_minutes: int = SESSION_GAP_MINUTES) -> float:
    """Gom các mốc thời gian gần nhau thành phiên liên tục, trả về tổng số phút."""
    timestamps = sorted(t for t in timestamps if t is not None)
    if not timestamps:
        return 0.0

    total_minutes = 0.0
    session_start = timestamps[0]
    last_time = timestamps[0]

    for t in timestamps[1:]:
        gap = (t - last_time).total_seconds() / 60
        if gap > gap_minutes:
            total_minutes += max((last_time - session_start).total_seconds() / 60, MIN_EVENT_MINUTES)
            session_start = t
        last_time = t

    total_minutes += max((last_time - session_start).total_seconds() / 60, MIN_EVENT_MINUTES)
    return total_minutes


def _estimate_study_hours(db: Session) -> float:
    """Ước tính tổng thời gian học TÍCH LŨY (mọi thời điểm) dựa trên hoạt động thực tế."""
    timestamps = [row[0] for row in db.query(models.StudyHistory.timestamp).all()]
    timestamps += [row[0] for row in db.query(models.ChatMessage.created_at).all()]
    return round(_sessionize(timestamps) / 60, 1)


def _estimate_today_minutes(db: Session) -> int:
    """Giống _estimate_study_hours nhưng chỉ tính các hoạt động xảy ra TRONG NGÀY HÔM NAY."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    timestamps = [
        row[0] for row in db.query(models.StudyHistory.timestamp)
        .filter(models.StudyHistory.timestamp >= today_start).all()
    ]
    timestamps += [
        row[0] for row in db.query(models.ChatMessage.created_at)
        .filter(models.ChatMessage.created_at >= today_start).all()
    ]
    return round(_sessionize(timestamps))


def _get_continue_learning(db: Session):
    """Tìm hoạt động luyện tập gần nhất (có gắn topic) để gợi ý 'Tiếp tục học'."""
    last_attempt = (
        db.query(models.StudyHistory)
        .join(models.Question)
        .filter(models.Question.topic.isnot(None))
        .order_by(models.StudyHistory.timestamp.desc())
        .first()
    )
    if not last_attempt:
        return None

    question = last_attempt.question
    subject = db.query(models.Subject).get(question.subject_id)
    return {
        "subject_id": question.subject_id,
        "subject_name": subject.name if subject else "",
        "topic": question.topic,
    }


@router.get("/analytics/overview")
async def analytics_overview(db: Session = Depends(get_db)):
    total_hours = _estimate_study_hours(db)

    # % đúng theo từng môn (tái dùng logic đã có ở /practice/stats)
    subjects = db.query(models.Subject).all()
    by_subject = []
    all_weak_topics = []  # gộp điểm yếu của MỌI môn để tìm ra cái yếu nhất tổng thể

    for s in subjects:
        attempts = (
            db.query(models.StudyHistory)
            .join(models.Question)
            .filter(models.Question.subject_id == s.id)
            .all()
        )
        percent = round(sum(1 for a in attempts if a.is_correct) / len(attempts) * 100) if attempts else None
        by_subject.append({"subject_id": s.id, "subject_name": s.name, "percent_correct": percent})

        # Lấy điểm yếu theo topic của môn này (giống /tutor/weak-topics nhưng gộp lại đây để tổng hợp)
        topic_rows = (
            db.query(models.Question.topic, models.StudyHistory.is_correct)
            .join(models.StudyHistory, models.StudyHistory.question_id == models.Question.id)
            .filter(models.Question.subject_id == s.id, models.Question.topic.isnot(None))
            .all()
        )
        topic_stats = {}
        for topic, is_correct in topic_rows:
            topic_stats.setdefault(topic, {"correct": 0, "total": 0})
            topic_stats[topic]["total"] += 1
            if is_correct:
                topic_stats[topic]["correct"] += 1
        for topic, stat in topic_stats.items():
            if stat["total"] >= 2:  # bỏ qua chủ đề mới làm 1 câu, chưa đủ tin cậy để kết luận "yếu"
                all_weak_topics.append({
                    "subject_id": s.id,
                    "subject_name": s.name,
                    "topic": topic,
                    "percent_correct": round(stat["correct"] / stat["total"] * 100),
                    "attempts": stat["total"],
                })

    # Tìm điểm yếu nhất TOÀN BỘ (tỉ lệ đúng thấp nhất), rồi gợi ý video liên quan luôn cho tiện
    weakest = None
    if all_weak_topics:
        all_weak_topics.sort(key=lambda x: x["percent_correct"])
        weakest = all_weak_topics[0]

        _, video_ids = _get_subject_source_ids(db, weakest["subject_id"])
        if video_ids:
            query_emb = await get_embedding(weakest["topic"])
            hits = query_within_sources(query_emb, video_ids=video_ids, n_results=1, content_type="video")
            if hits:
                weakest["suggested_video"] = {
                    "source_name": hits[0]["source_name"],
                    "timestamp": format_timestamp(hits[0]["start_time"]),
                }

    return {
        "total_hours_estimated": total_hours,
        "today_minutes": _estimate_today_minutes(db),
        "daily_goal_minutes": DAILY_GOAL_MINUTES,
        "continue_learning": _get_continue_learning(db),
        "by_subject": by_subject,
        "weakest_point": weakest,
    }
