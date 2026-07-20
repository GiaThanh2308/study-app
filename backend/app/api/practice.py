import random
import json
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models import models, schemas
from app.ai.rag.vector_store import get_chunks_for_source
from app.ai.ollama_client import chat_stream

router = APIRouter()


# ---------- AI tự tạo câu hỏi (dạng nháp, người dùng xem lại trước khi lưu) ----------
class GenerateAiRequest(BaseModel):
    subject_id: int
    document_id: int | None = None
    video_id: int | None = None
    count: int = 5


AI_QUESTION_PROMPT = """Dựa trên nội dung tài liệu dưới đây, hãy tạo ra {count} câu hỏi trắc nghiệm
(4 đáp án, chỉ 1 đáp án đúng) bằng tiếng Việt, phù hợp để ôn thi THPT.

Trả lời CHỈ bằng JSON hợp lệ theo đúng định dạng sau, không thêm chữ nào khác ngoài JSON:
[
  {{
    "content": "Nội dung câu hỏi",
    "answers": [
      {{"content": "Đáp án A", "is_correct": false}},
      {{"content": "Đáp án B", "is_correct": true}},
      {{"content": "Đáp án C", "is_correct": false}},
      {{"content": "Đáp án D", "is_correct": false}}
    ],
    "explanation": "Giải thích ngắn gọn vì sao đáp án đó đúng"
  }}
]

NỘI DUNG TÀI LIỆU:
{context}
"""


async def _call_ai_generate_questions(context: str, count: int) -> list[dict]:
    """Gọi AI soạn câu hỏi từ 1 đoạn nội dung, trả về list dict đã parse JSON. Dùng chung cho cả
    'AI tạo câu hỏi' (1 tài liệu) và 'Tạo đề thi thử' (nhiều file gộp lại)."""
    prompt = AI_QUESTION_PROMPT.format(count=count, context=context)

    full_response = ""
    async for chunk in chat_stream([{"role": "user", "content": prompt}]):
        full_response += chunk

    try:
        start = full_response.index("[")
        end = full_response.rindex("]") + 1
        return json.loads(full_response[start:end])
    except (ValueError, json.JSONDecodeError):
        return []  # để hàm gọi tự quyết định báo lỗi hay bỏ qua nguồn này


@router.post("/practice/generate-ai")
async def generate_ai_questions(payload: GenerateAiRequest):
    chunks = get_chunks_for_source(document_id=payload.document_id, video_id=payload.video_id, limit=8)
    if not chunks:
        raise HTTPException(400, "Chưa có nội dung nào được xử lý AI cho tài liệu/video này. Vào 'Môn học' xử lý trước.")

    context = "\n\n".join(chunks)
    parsed = await _call_ai_generate_questions(context, payload.count)
    if not parsed:
        raise HTTPException(500, "AI trả về định dạng không hợp lệ, thử lại hoặc giảm số câu hỏi yêu cầu.")

    # Trả về dạng nháp — CHƯA lưu vào database, người dùng xem lại rồi tự lưu từng câu qua /practice/questions
    return {"subject_id": payload.subject_id, "draft_questions": parsed}


def _strip_correct_flag(questions: list[models.Question]):
    """Xóa is_correct khỏi response lúc làm bài — tránh lộ đáp án qua Network tab của trình duyệt."""
    for q in questions:
        for a in q.answers:
            a.is_correct = False
    return questions


# ---------- Tạo đề thi thử: chọn ngẫu nhiên nhiều file đề, mỗi file vài câu ----------
class GenerateExamRequest(BaseModel):
    subject_id: int
    num_files: int = 3          # số file đề PDF lấy ngẫu nhiên
    questions_per_file: int = 3  # số câu hỏi AI soạn từ mỗi file


@router.post("/practice/generate-exam")
async def generate_exam(payload: GenerateExamRequest, db: Session = Depends(get_db)):
    # Chỉ lấy các file loại "exam" (đề thi) đã xử lý AI xong (Giai đoạn 4), thuộc đúng môn học
    # Tìm file đề thi qua 2 đường: (1) subject_id gán trực tiếp trên Document (upload không qua bài học),
    # (2) qua quan hệ Lesson -> Chapter -> Subject (trường hợp phổ biến: upload đề thi vào 1 bài học cụ thể).
    exam_docs_direct = (
        db.query(models.Document)
        .filter(
            models.Document.subject_id == payload.subject_id,
            models.Document.doc_type == "exam",
            models.Document.rag_status == "ready",
        )
        .all()
    )
    exam_docs_via_lesson = (
        db.query(models.Document)
        .join(models.Lesson, models.Document.lesson_id == models.Lesson.id)
        .join(models.Chapter, models.Lesson.chapter_id == models.Chapter.id)
        .filter(
            models.Chapter.subject_id == payload.subject_id,
            models.Document.doc_type == "exam",
            models.Document.rag_status == "ready",
        )
        .all()
    )
    # Gộp 2 danh sách, loại trùng theo id
    exam_docs = list({d.id: d for d in exam_docs_direct + exam_docs_via_lesson}.values())
    if not exam_docs:
        raise HTTPException(
            400,
            "Chưa có file đề thi nào (doc_type='exam') đã xử lý AI cho môn này. "
            "Vào 'Môn học', upload đề thi dạng PDF và bấm 'Xử lý AI' trước.",
        )

    selected_docs = random.sample(exam_docs, min(payload.num_files, len(exam_docs)))

    all_question_ids = []
    failed_sources = []

    for doc in selected_docs:
        chunks = get_chunks_for_source(document_id=doc.id, limit=6)
        if not chunks:
            failed_sources.append(doc.original_filename)
            continue

        context = "\n\n".join(chunks)
        parsed = await _call_ai_generate_questions(context, payload.questions_per_file)
        if not parsed:
            failed_sources.append(doc.original_filename)
            continue

        for item in parsed:
            question = models.Question(
                subject_id=payload.subject_id,
                content=item.get("content", ""),
                question_type="mcq",
                source="ai_generated",
                explanation=item.get("explanation"),
            )
            db.add(question)
            db.flush()
            for a in item.get("answers", []):
                db.add(models.Answer(question_id=question.id, content=a.get("content", ""), is_correct=a.get("is_correct", False)))
            all_question_ids.append(question.id)

    db.commit()

    if not all_question_ids:
        raise HTTPException(500, "AI không tạo được câu hỏi nào từ các file đề đã chọn, thử lại.")

    return {
        "question_ids": all_question_ids,
        "total_questions": len(all_question_ids),
        "source_files": [d.original_filename for d in selected_docs],
        "failed_sources": failed_sources,  # file nào AI tạo lỗi, bị bỏ qua (vẫn có câu từ các file khác)
    }


@router.get("/practice/questions/by-ids", response_model=list[schemas.QuestionOut])
def get_questions_by_ids(ids: str, db: Session = Depends(get_db)):
    """Lấy câu hỏi theo danh sách ID (dùng khi làm đề thi thử) — ẩn đáp án đúng, giống /practice/quiz."""
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    questions = (
        db.query(models.Question)
        .options(joinedload(models.Question.answers))
        .filter(models.Question.id.in_(id_list))
        .all()
    )
    # Giữ đúng thứ tự theo id_list gốc (query .in_() không đảm bảo thứ tự)
    by_id = {q.id: q for q in questions}
    ordered = [by_id[i] for i in id_list if i in by_id]
    return _strip_correct_flag(ordered)


# ---------- Nhập tay câu hỏi ----------
@router.post("/practice/questions", response_model=schemas.QuestionOut)
def create_question(payload: schemas.QuestionCreate, db: Session = Depends(get_db)):
    question = models.Question(
        subject_id=payload.subject_id,
        content=payload.content,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        explanation=payload.explanation,
        source="manual",
    )
    db.add(question)
    db.flush()  # để lấy question.id trước khi thêm answers

    for a in payload.answers:
        db.add(models.Answer(question_id=question.id, content=a.content, is_correct=a.is_correct))

    db.commit()
    db.refresh(question)
    return question


@router.get("/practice/questions", response_model=list[schemas.QuestionOut])
def list_questions(subject_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Question).options(joinedload(models.Question.answers))
    if subject_id:
        query = query.filter(models.Question.subject_id == subject_id)
    return query.all()


@router.delete("/practice/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(models.Question).get(question_id)
    if not q:
        raise HTTPException(404, "Câu hỏi không tồn tại")
    db.delete(q)
    db.commit()
    return {"ok": True}


# ---------- Lấy đề luyện tập (random N câu) ----------
@router.get("/practice/quiz", response_model=list[schemas.QuestionOut])
def get_quiz(subject_id: int, count: int = 10, db: Session = Depends(get_db)):
    questions = (
        db.query(models.Question)
        .options(joinedload(models.Question.answers))
        .filter(models.Question.subject_id == subject_id)
        .all()
    )
    random.shuffle(questions)
    selected = questions[:count]
    return _strip_correct_flag(selected)


# ---------- Nộp đáp án, chấm điểm, tự lưu lỗi sai ----------
@router.post("/practice/submit", response_model=schemas.SubmitAnswerResult)
def submit_answer(payload: schemas.SubmitAnswerRequest, db: Session = Depends(get_db)):
    question = db.query(models.Question).options(joinedload(models.Question.answers)).get(payload.question_id)
    if not question:
        raise HTTPException(404, "Câu hỏi không tồn tại")

    correct_answer = next((a for a in question.answers if a.is_correct), None)
    if not correct_answer:
        raise HTTPException(400, "Câu hỏi này chưa có đáp án đúng được đánh dấu")

    is_correct = payload.answer_id == correct_answer.id

    # Lưu lịch sử — đây chính là cơ chế "Sổ lỗi sai": chỉ cần lọc is_correct=False là ra danh sách lỗi
    history = models.StudyHistory(question_id=question.id, is_correct=is_correct)
    db.add(history)
    db.commit()

    return schemas.SubmitAnswerResult(
        is_correct=is_correct,
        correct_answer_id=correct_answer.id,
        explanation=question.explanation,
    )


# ---------- Sổ lỗi sai ----------
@router.get("/practice/mistakes", response_model=list[schemas.QuestionOut])
def get_mistake_book(subject_id: int | None = None, db: Session = Depends(get_db)):
    """
    Trả về các câu hỏi mà LẦN GẦN NHẤT làm bị sai (nếu sau đó làm lại đúng thì tự
    'tốt nghiệp' khỏi sổ lỗi, không cần thao tác xóa thủ công).
    """
    # Lấy question_id kèm is_correct của lần làm gần nhất cho mỗi câu hỏi
    subquery = (
        db.query(
            models.StudyHistory.question_id,
            models.StudyHistory.is_correct,
        )
        .order_by(models.StudyHistory.question_id, models.StudyHistory.timestamp.desc())
        .all()
    )
    latest_result = {}
    for question_id, is_correct in subquery:
        if question_id not in latest_result:  # bản ghi đầu tiên gặp là mới nhất (đã sort desc)
            latest_result[question_id] = is_correct

    wrong_question_ids = [qid for qid, correct in latest_result.items() if not correct]
    if not wrong_question_ids:
        return []

    query = (
        db.query(models.Question)
        .options(joinedload(models.Question.answers))
        .filter(models.Question.id.in_(wrong_question_ids))
    )
    if subject_id:
        query = query.filter(models.Question.subject_id == subject_id)
    return query.all()


# ---------- Thống kê nhanh cho Dashboard ----------
@router.get("/practice/stats")
def get_practice_stats(db: Session = Depends(get_db)):
    total_attempts = db.query(models.StudyHistory).count()
    correct_attempts = db.query(models.StudyHistory).filter(models.StudyHistory.is_correct == True).count()

    stats_by_subject = []
    subjects = db.query(models.Subject).all()
    for s in subjects:
        attempts = (
            db.query(models.StudyHistory)
            .join(models.Question)
            .filter(models.Question.subject_id == s.id)
            .all()
        )
        if attempts:
            correct = sum(1 for a in attempts if a.is_correct)
            percent = round(correct / len(attempts) * 100)
        else:
            percent = None
        stats_by_subject.append({"subject_id": s.id, "subject_name": s.name, "percent_correct": percent})

    return {
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "overall_percent": round(correct_attempts / total_attempts * 100) if total_attempts else None,
        "by_subject": stats_by_subject,
    }
