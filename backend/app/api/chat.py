"""Chat AI với tích hợp RAG định vị chính xác (YouTube timestamp, PDF page),
phát hiện nhu cầu làm đề thi và công cụ import đề từ hình ảnh mạng xã hội."""
import logging
import json
import re
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.core.database import get_db, SessionLocal
from app.models import models
from app.ai.ollama_client import chat_stream, check_ollama_available
from app.ai.rag import search_knowledge, build_rag_prompt
from app.ai.vision_parser import process_exam_image
from app.ai.youtube_harvester import fetch_youtube_transcript, index_youtube_lecture, extract_youtube_id

logger = logging.getLogger("studyapp.chat")
router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class YouTubeImportRequest(BaseModel):
    lesson_id: int
    youtube_url: str
    title: str


@router.get("/chat/status")
async def chat_status():
    available = await check_ollama_available()
    return {"ollama_running": available}


@router.get("/chat/history")
def chat_history(limit: int = 50, db: Session = Depends(get_db)):
    messages = (
        db.query(models.ChatMessage)
        .order_by(models.ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


@router.delete("/chat/history")
def clear_chat_history(db: Session = Depends(get_db)):
    db.query(models.ChatMessage).delete()
    db.commit()
    return {"ok": True}


def find_matching_exams(db: Session, query: str):
    """Phát hiện ý định muốn làm đề thi và tìm đề phù hợp từ database."""
    q_lower = query.lower()
    exam_triggers = ["đề thi", "làm đề", "bài kiểm tra", "làm bài", "thi thử", "tốt nghiệp", "luyện đề", "bài test", "đề ôn"]
    
    is_exam_request = any(trigger in q_lower for trigger in exam_triggers)
    if not is_exam_request:
        return []

    subject_id = None
    if "toán" in q_lower:
        s = db.query(models.Subject).filter(models.Subject.name.ilike("%toán%")).first()
        if s: subject_id = s.id
    elif "lý" in q_lower or "vật lý" in q_lower:
        s = db.query(models.Subject).filter(models.Subject.name.ilike("%lý%")).first()
        if s: subject_id = s.id
    elif "hóa" in q_lower or "hóa học" in q_lower:
        s = db.query(models.Subject).filter(models.Subject.name.ilike("%hóa%")).first()
        if s: subject_id = s.id

    query_builder = db.query(models.Exam)
    if subject_id:
        query_builder = query_builder.filter(models.Exam.subject_id == subject_id)

    if "tốt nghiệp" in q_lower or "quốc gia" in q_lower:
        query_builder = query_builder.filter(
            or_(models.Exam.exam_type == "national", models.Exam.title.ilike("%tốt nghiệp%"))
        )
    elif "thi thử" in q_lower:
        query_builder = query_builder.filter(
            or_(models.Exam.exam_type == "mock", models.Exam.title.ilike("%thi thử%"))
        )

    topic_keywords = ["đạo hàm", "tích phân", "số phức", "mũ", "logarit", "hình không gian",
                      "dao động", "sóng cơ", "điện xoay chiều", "quang học", "hạt nhân",
                      "este", "lipit", "cacbohidrat", "amino axit", "kim loại", "peptit"]
    
    matched_topics = [kw for kw in topic_keywords if kw in q_lower]
    exams = query_builder.limit(4).all()

    if not exams and matched_topics:
        topic = matched_topics[0]
        exam_ids_with_topic = (
            db.query(models.ExamQuestion.exam_id)
            .filter(
                or_(
                    models.ExamQuestion.topic_tag.ilike(f"%{topic}%"),
                    models.ExamQuestion.question_text.ilike(f"%{topic}%"),
                )
            )
            .distinct()
            .all()
        )
        ids = [row[0] for row in exam_ids_with_topic]
        if ids:
            exams = db.query(models.Exam).filter(models.Exam.id.in_(ids)).limit(3).all()

    if not exams and subject_id:
        exams = db.query(models.Exam).filter(models.Exam.subject_id == subject_id).limit(3).all()

    results = []
    for e in exams:
        subj = db.get(models.Subject, e.subject_id)
        results.append({
            "id": e.id,
            "title": e.title,
            "subject_name": subj.name if subj else "",
            "subject_icon": subj.icon if subj else "📝",
            "duration_minutes": e.duration_minutes,
            "total_questions": e.total_questions,
            "exam_type": e.exam_type,
            "description": e.description,
            "province": e.province,
            "school_or_dept": e.school_or_dept,
            "exam_year": e.exam_year,
            "curriculum_standard": e.curriculum_standard,
        })
    return results


@router.post("/chat/send")
async def chat_send(payload: ChatRequest, db: Session = Depends(get_db)):
    user_msg = models.ChatMessage(role="user", content=payload.message)
    db.add(user_msg)
    db.commit()

    matching_exams = find_matching_exams(db, payload.message)

    # RAG: Tìm kiếm có tọa độ vị trí (phút, giây, trang)
    rag_results = search_knowledge(db, payload.message, limit=3)
    
    exam_context = ""
    if matching_exams:
        exam_list_str = "\n".join([f"- Đề #{e['id']}: {e['title']} ({e['subject_name']})" for e in matching_exams])
        exam_context = f"\n\nTìm thấy đề thi liên quan:\n{exam_list_str}\nHãy mời học sinh bấm vào thẻ đề thi bên dưới để làm bài."

    enhanced_message = build_rag_prompt(payload.message, rag_results) + exam_context

    history = (
        db.query(models.ChatMessage)
        .order_by(models.ChatMessage.id.desc())
        .limit(20)
        .all()
    )
    history.reverse()

    messages = []
    for m in history[:-1]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": enhanced_message})

    # Lọc ra danh sách media liên quan (Video YouTube có timestamp, PDF có số trang)
    media_attachments = []
    seen_media = set()
    for r in rag_results:
        # Nếu là video YouTube
        if r.get("youtube_id"):
            key = f"yt_{r['youtube_id']}_{r['timestamp_start']}"
            if key not in seen_media:
                seen_media.add(key)
                media_attachments.append({
                    "type": "youtube",
                    "youtube_id": r["youtube_id"],
                    "timestamp_start": r.get("timestamp_start", 0),
                    "title": r.get("lesson_title") or "Video bài giảng",
                    "chapter_name": r.get("chapter_name"),
                })
        elif r.get("video_path"):
            key = f"local_{r['video_path']}_{r['timestamp_start']}"
            if key not in seen_media:
                seen_media.add(key)
                media_attachments.append({
                    "type": "video",
                    "video_path": r["video_path"],
                    "timestamp_start": r.get("timestamp_start", 0),
                    "title": r.get("lesson_title") or "Video bài giảng",
                })
        elif r.get("page_number"):
            media_attachments.append({
                "type": "pdf",
                "page_number": r["page_number"],
                "title": r.get("lesson_title") or "Tài liệu học tập",
            })

    async def event_generator():
        full_response = ""
        try:
            async for chunk in chat_stream(messages):
                full_response += chunk
                yield chunk
        except Exception as e:
            error_msg = f"\n\n⚠️ Lỗi kết nối AI: {str(e)}"
            full_response += error_msg
            yield error_msg

        try:
            save_db = SessionLocal()

            # Gắn metadata thẻ đề thi nếu có
            if matching_exams:
                json_exam_tag = f"\n\n<!--EXAM_RECOMMENDATION:{json.dumps(matching_exams, ensure_ascii=False)}-->"
                full_response += json_exam_tag
                yield json_exam_tag

            # Gắn metadata video nhúng / tài liệu định vị chính xác
            if media_attachments:
                json_media_tag = f"\n\n<!--MEDIA_ATTACHMENTS:{json.dumps(media_attachments, ensure_ascii=False)}-->"
                full_response += json_media_tag
                yield json_media_tag

            assistant_msg = models.ChatMessage(role="assistant", content=full_response)
            save_db.add(assistant_msg)
            save_db.commit()
        except Exception as e:
            logger.error(f"Lỗi lưu chat response: {e}")
        finally:
            save_db.close()

    return StreamingResponse(event_generator(), media_type="text/plain")


# ===================== CÁC CÔNG CỤ THU THẬP TỰ ĐỘNG (INTERNET & SOCIAL) =====================

@router.post("/chat/import-exam-image")
async def import_exam_from_image(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Tải ảnh đề thi chụp từ Facebook/điện thoại ➔ Vision AI đọc chữ và tạo đề trắc nghiệm ngay lập tức.
    """
    image_bytes = await file.read()
    exam = await process_exam_image(
        db=db,
        subject_id=subject_id,
        image_bytes=image_bytes,
        exam_title=f"Đề quét từ ảnh: {file.filename[:30]}",
    )
    return {
        "success": True,
        "exam_id": exam.id,
        "title": exam.title,
        "total_questions": exam.total_questions,
        "message": f"Đã bóc tách thành công {exam.total_questions} câu hỏi từ ảnh đề thi!",
    }


@router.post("/harvester/import-youtube")
async def import_youtube_video(payload: YouTubeImportRequest, db: Session = Depends(get_db)):
    """
    Dán link YouTube bài giảng ➔ Tự động bóc tách transcript và mốc thời gian từng giây (Zero Disk).
    """
    video_id = extract_youtube_id(payload.youtube_url)
    if not video_id:
        raise HTTPException(400, "URL YouTube không hợp lệ.")

    transcript_items = await fetch_youtube_transcript(video_id)
    video = index_youtube_lecture(
        db=db,
        lesson_id=payload.lesson_id,
        youtube_url=payload.youtube_url,
        title=payload.title,
        transcript_items=transcript_items,
    )
    return {
        "success": True,
        "video_id": video.id,
        "youtube_id": video_id,
        "transcript_count": len(transcript_items),
        "message": f"Đã thu thập bài giảng YouTube và tạo mốc thời gian thành công ({len(transcript_items)} câu thoại)!",
    }
