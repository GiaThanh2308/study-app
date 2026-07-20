import json
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models import models
from app.ai.rag.embeddings import get_embedding
from app.ai.rag.vector_store import query_within_sources
from app.ai.ollama_client import chat_stream
from app.ai.video.whisper_transcribe import format_timestamp
from app.api.practice import _call_ai_generate_questions, _strip_correct_flag

router = APIRouter()


def _get_subject_source_ids(db: Session, subject_id: int):
    """Lấy toàn bộ document_id và video_id thuộc 1 môn học (qua cả 2 đường: gán trực tiếp và qua bài học)."""
    docs_direct = db.query(models.Document.id).filter(models.Document.subject_id == subject_id).all()
    docs_via_lesson = (
        db.query(models.Document.id)
        .join(models.Lesson, models.Document.lesson_id == models.Lesson.id)
        .join(models.Chapter, models.Lesson.chapter_id == models.Chapter.id)
        .filter(models.Chapter.subject_id == subject_id)
        .all()
    )
    document_ids = list({row[0] for row in docs_direct + docs_via_lesson})

    videos_via_lesson = (
        db.query(models.Video.id)
        .join(models.Lesson, models.Video.lesson_id == models.Lesson.id)
        .join(models.Chapter, models.Lesson.chapter_id == models.Chapter.id)
        .filter(models.Chapter.subject_id == subject_id)
        .all()
    )
    video_ids = [row[0] for row in videos_via_lesson]

    return document_ids, video_ids


# ---------- 1. Phát hiện điểm yếu ----------
@router.get("/tutor/weak-topics")
def get_weak_topics(subject_id: int, db: Session = Depends(get_db)):
    """
    Gộp lịch sử làm bài theo 'topic' của câu hỏi, tính tỉ lệ đúng, sắp xếp YẾU NHẤT lên đầu.
    Chỉ tính các câu hỏi có gắn topic (câu AI Tutor tạo ra, hoặc câu nhập tay có điền topic).
    """
    rows = (
        db.query(models.Question.topic, models.StudyHistory.is_correct)
        .join(models.StudyHistory, models.StudyHistory.question_id == models.Question.id)
        .filter(models.Question.subject_id == subject_id, models.Question.topic.isnot(None))
        .all()
    )

    topic_stats = {}
    for topic, is_correct in rows:
        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0}
        topic_stats[topic]["total"] += 1
        if is_correct:
            topic_stats[topic]["correct"] += 1

    result = [
        {"topic": t, "percent_correct": round(s["correct"] / s["total"] * 100), "attempts": s["total"]}
        for t, s in topic_stats.items()
    ]
    result.sort(key=lambda x: x["percent_correct"])  # yếu nhất (thấp nhất) lên đầu
    return result


# ---------- 2. Tạo bài tập nhắm đúng chủ đề ----------
class TutorGenerateRequest(BaseModel):
    subject_id: int
    topic: str
    count: int = 10


@router.post("/tutor/generate")
async def tutor_generate(payload: TutorGenerateRequest, db: Session = Depends(get_db)):
    document_ids, video_ids = _get_subject_source_ids(db, payload.subject_id)
    if not document_ids and not video_ids:
        raise HTTPException(400, "Môn học này chưa có tài liệu/video nào đã xử lý AI để tạo bài tập.")

    query_emb = await get_embedding(payload.topic)
    hits = query_within_sources(query_emb, document_ids=document_ids, video_ids=video_ids, n_results=8)
    if not hits:
        raise HTTPException(400, f"Không tìm thấy nội dung liên quan tới '{payload.topic}' trong tài liệu đã xử lý.")

    context = "\n\n".join(h["text"] for h in hits)
    parsed = await _call_ai_generate_questions(context, payload.count)
    if not parsed:
        raise HTTPException(500, "AI không tạo được câu hỏi, thử lại hoặc đổi cách diễn đạt chủ đề.")

    question_ids = []
    for item in parsed:
        question = models.Question(
            subject_id=payload.subject_id,
            content=item.get("content", ""),
            question_type="mcq",
            source="ai_generated",
            topic=payload.topic,
            explanation=item.get("explanation"),
        )
        db.add(question)
        db.flush()
        for a in item.get("answers", []):
            db.add(models.Answer(question_id=question.id, content=a.get("content", ""), is_correct=a.get("is_correct", False)))
        question_ids.append(question.id)

    db.commit()
    return {"topic": payload.topic, "question_ids": question_ids, "total_questions": len(question_ids)}


# ---------- 3. Giải thích sâu hơn khi làm sai ----------
class ExplainRequest(BaseModel):
    question_id: int
    chosen_answer_id: int


@router.post("/tutor/explain")
async def tutor_explain(payload: ExplainRequest, db: Session = Depends(get_db)):
    question = db.query(models.Question).options(joinedload(models.Question.answers)).get(payload.question_id)
    if not question:
        raise HTTPException(404, "Câu hỏi không tồn tại")

    chosen = next((a for a in question.answers if a.id == payload.chosen_answer_id), None)
    correct = next((a for a in question.answers if a.is_correct), None)

    prompt = f"""Bạn là gia sư. Học sinh làm câu hỏi sau và chọn SAI đáp án. Hãy giải thích thật dễ hiểu,
từng bước, vì sao đáp án học sinh chọn SAI và vì sao đáp án đúng là ĐÚNG. Trả lời bằng tiếng Việt, ngắn gọn.

Câu hỏi: {question.content}
Đáp án học sinh chọn (SAI): {chosen.content if chosen else "?"}
Đáp án đúng: {correct.content if correct else "?"}
Giải thích có sẵn (nếu có): {question.explanation or "(không có)"}
"""

    full_response = ""
    async for chunk in chat_stream([{"role": "user", "content": prompt}]):
        full_response += chunk

    return {"explanation": full_response}


# ---------- 4. Gợi ý video liên quan tới chủ đề ----------
@router.get("/tutor/suggest-video")
async def suggest_video(subject_id: int, topic: str, db: Session = Depends(get_db)):
    _, video_ids = _get_subject_source_ids(db, subject_id)
    if not video_ids:
        return {"suggestions": []}

    query_emb = await get_embedding(topic)
    hits = query_within_sources(query_emb, video_ids=video_ids, n_results=3, content_type="video")

    suggestions = [
        {"source_name": h["source_name"], "timestamp": format_timestamp(h["start_time"]), "start_seconds": h["start_time"]}
        for h in hits
    ]
    return {"suggestions": suggestions}
