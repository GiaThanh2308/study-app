from datetime import timedelta
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


def _estimate_study_hours(db: Session) -> float:
    """
    Ước tính tổng thời gian học dựa trên timestamp của StudyHistory (làm bài) và ChatMessage (hỏi AI).
    Gom các hoạt động gần nhau thành 1 phiên, cộng dồn thời lượng — vì hệ thống không có cách nào
    biết chính xác người dùng ngồi học bao lâu, đây là cách ước lượng hợp lý dựa trên hoạt động thực tế.
    """
    timestamps = []
    for row in db.query(models.StudyHistory.timestamp).all():
        timestamps.append(row[0])
    for row in db.query(models.ChatMessage.created_at).all():
        timestamps.append(row[0])

    if not timestamps:
        return 0.0

    timestamps = sorted(t for t in timestamps if t is not None)
    total_minutes = 0.0
    session_start = timestamps[0]
    last_time = timestamps[0]

    for t in timestamps[1:]:
        gap = (t - last_time).total_seconds() / 60
        if gap > SESSION_GAP_MINUTES:
            # Kết thúc phiên trước, cộng dồn (tối thiểu MIN_EVENT_MINUTES nếu phiên chỉ có 1 hoạt động)
            session_length = max((last_time - session_start).total_seconds() / 60, MIN_EVENT_MINUTES)
            total_minutes += session_length
            session_start = t
        last_time = t

    # Cộng nốt phiên cuối cùng
    session_length = max((last_time - session_start).total_seconds() / 60, MIN_EVENT_MINUTES)
    total_minutes += session_length

    return round(total_minutes / 60, 1)


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
        "by_subject": by_subject,
        "weakest_point": weakest,
    }
