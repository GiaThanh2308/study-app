import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models import models, schemas
from app.ai.ollama_client import chat_stream
from app.ai.rag.vector_store import get_chunks_for_source

router = APIRouter()


# ======================================================================
# Helpers dùng chung (AI Gia sư ở tutor.py cũng import 2 hàm bên dưới)
# ======================================================================
def _strip_correct_flag(questions: list[models.Question]):
    """Ẩn is_correct trước khi trả về cho client khi làm bài (không lộ đáp án)."""
    out = []
    for q in questions:
        out.append(schemas.QuestionOut(
            id=q.id, subject_id=q.subject_id, content=q.content, question_type=q.question_type,
            difficulty=q.difficulty, source=q.source, explanation=None,
            answers=[schemas.AnswerOut(id=a.id, content=a.content, is_correct=False) for a in q.answers],
        ))
    return out


async def _call_ai_generate_questions(context: str, count: int):
    prompt = f"""Dựa trên nội dung sau, hãy soạn {count} câu hỏi trắc nghiệm 4 đáp án (chỉ 1 đáp án đúng),
bám sát nội dung, độ khó tăng dần. Trả lời CHỈ bằng JSON hợp lệ, không thêm chữ nào khác, đúng định dạng:
[
  {{"content": "...", "answers": [{{"content":"...","is_correct":true}}, {{"content":"...","is_correct":false}}, {{"content":"...","is_correct":false}}, {{"content":"...","is_correct":false}}], "explanation": "..."}}
]

Nội dung:
{context}
"""
    full_response = ""
    async for chunk in chat_stream([{"role": "user", "content": prompt}]):
        full_response += chunk
    try:
        start = full_response.index("[")
        end = full_response.rindex("]") + 1
        return json.loads(full_response[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


# ======================================================================
# Câu hỏi theo ID / nộp 1 câu — vẫn giữ, dùng cho tab "AI Gia sư"
# ======================================================================
@router.get("/practice/questions/by-ids", response_model=list[schemas.QuestionOut])
def get_questions_by_ids(ids: str, db: Session = Depends(get_db)):
    id_list = [int(x) for x in ids.split(",") if x.strip()]
    questions = (
        db.query(models.Question)
        .options(joinedload(models.Question.answers))
        .filter(models.Question.id.in_(id_list))
        .all()
    )
    order = {qid: i for i, qid in enumerate(id_list)}
    questions.sort(key=lambda q: order.get(q.id, 0))
    return _strip_correct_flag(questions)


@router.post("/practice/submit", response_model=schemas.SubmitAnswerResult)
def submit_answer(payload: schemas.SubmitAnswerRequest, db: Session = Depends(get_db)):
    question = db.query(models.Question).options(joinedload(models.Question.answers)).get(payload.question_id)
    if not question:
        raise HTTPException(404, "Câu hỏi không tồn tại")
    correct = next((a for a in question.answers if a.is_correct), None)
    is_correct = bool(correct and correct.id == payload.answer_id)
    db.add(models.StudyHistory(question_id=question.id, is_correct=is_correct))
    db.commit()
    return schemas.SubmitAnswerResult(
        is_correct=is_correct,
        correct_answer_id=correct.id if correct else 0,
        explanation=question.explanation,
    )


# ======================================================================
# TẠO ĐỀ THI BẰNG AI — quét toàn bộ tài liệu đã upload của môn học,
# tạo đề đúng cấu trúc THPT Quốc Gia (3 phần), chấm điểm thật khi nộp bài.
# ======================================================================
def _get_subject_sources(db: Session, subject_id: int):
    docs_direct = db.query(models.Document).filter(
        models.Document.subject_id == subject_id, models.Document.rag_status == "ready"
    ).all()
    docs_via_lesson = (
        db.query(models.Document)
        .join(models.Lesson, models.Document.lesson_id == models.Lesson.id)
        .join(models.Chapter, models.Lesson.chapter_id == models.Chapter.id)
        .filter(models.Chapter.subject_id == subject_id, models.Document.rag_status == "ready")
        .all()
    )
    documents = list({d.id: d for d in docs_direct + docs_via_lesson}.values())

    videos = (
        db.query(models.Video)
        .join(models.Lesson, models.Video.lesson_id == models.Lesson.id)
        .join(models.Chapter, models.Lesson.chapter_id == models.Chapter.id)
        .filter(models.Chapter.subject_id == subject_id, models.Video.rag_status == "ready")
        .all()
    )
    return documents, videos


def _collect_subject_context(db: Session, subject_id: int, max_chunks_per_source: int = 4, max_sources: int = 14):
    documents, videos = _get_subject_sources(db, subject_id)
    sources = [("document", d.id, d.original_filename or f"Tài liệu #{d.id}") for d in documents]
    sources += [("video", v.id, v.original_filename or f"Video #{v.id}") for v in videos]
    if not sources:
        return "", []

    sources = sources[:max_sources]
    parts, used_names = [], []
    for kind, sid, name in sources:
        chunks = (
            get_chunks_for_source(document_id=sid, limit=max_chunks_per_source)
            if kind == "document"
            else get_chunks_for_source(video_id=sid, limit=max_chunks_per_source)
        )
        if chunks:
            parts.append(f"--- Nguồn: {name} ---\n" + "\n".join(chunks))
            used_names.append(name)
    return "\n\n".join(parts), used_names


EXAM_PROMPT = """Bạn là chuyên gia ra đề thi THPT Quốc Gia Việt Nam. Dựa trên TOÀN BỘ nội dung tài liệu dưới đây
(lấy từ nhiều file/video khác nhau của cùng 1 môn học), hãy soạn 1 đề thi thử ĐÚNG CẤU TRÚC đề thi THPT hiện hành,
gồm 3 phần:

- PHẦN I — Trắc nghiệm nhiều lựa chọn: {part1_count} câu, mỗi câu có đúng 4 phương án (A,B,C,D), chỉ 1 phương án đúng.
- PHẦN II — Đúng/Sai: {part2_count} câu, mỗi câu có 1 đoạn dẫn/tình huống và ĐÚNG 4 ý nhỏ (a,b,c,d), mỗi ý là 1 phát
  biểu đúng hoặc sai ĐỘC LẬP với nhau (không phải chọn 1 trong 4 như trắc nghiệm thường).
- PHẦN III — Trả lời ngắn: {part3_count} câu, đáp án là 1 số/kết quả/từ ngắn gọn (không phải tự luận dài).

Toàn bộ câu hỏi PHẢI bám sát nội dung tài liệu cung cấp, độ khó tăng dần trong mỗi phần, phù hợp ôn thi THPT
Quốc Gia. Trả lời CHỈ bằng JSON hợp lệ theo đúng định dạng sau, không thêm chữ nào khác ngoài JSON:

{{
  "part1": [
    {{"content": "Nội dung câu hỏi", "answers": [
        {{"content": "Đáp án A", "is_correct": false}},
        {{"content": "Đáp án B", "is_correct": true}},
        {{"content": "Đáp án C", "is_correct": false}},
        {{"content": "Đáp án D", "is_correct": false}}
      ], "explanation": "Giải thích ngắn gọn"}}
  ],
  "part2": [
    {{"content": "Đoạn dẫn/tình huống chung cho 4 ý bên dưới", "statements": [
        {{"content": "a) ...", "is_correct": true}},
        {{"content": "b) ...", "is_correct": false}},
        {{"content": "c) ...", "is_correct": true}},
        {{"content": "d) ...", "is_correct": false}}
      ], "explanation": "Giải thích ngắn gọn"}}
  ],
  "part3": [
    {{"content": "Nội dung câu hỏi", "correct_answer": "Đáp số ngắn gọn", "explanation": "Giải thích ngắn gọn"}}
  ]
}}

NỘI DUNG TÀI LIỆU (nhiều nguồn):
{context}
"""


@router.post("/practice/exams/generate", response_model=schemas.ExamSummary)
async def generate_exam(payload: schemas.ExamGenerateRequest, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).get(payload.subject_id)
    if not subject:
        raise HTTPException(404, "Môn học không tồn tại")

    context, source_names = _collect_subject_context(db, payload.subject_id)
    if not context:
        raise HTTPException(
            400,
            "Môn học này chưa có tài liệu/video nào đã xử lý AI (RAG). Vào 'Môn học', upload file và bấm 'Xử lý AI' trước.",
        )

    prompt = EXAM_PROMPT.format(
        part1_count=payload.part1_count,
        part2_count=payload.part2_count,
        part3_count=payload.part3_count,
        context=context[:16000],
    )

    full_response = ""
    async for chunk in chat_stream([{"role": "user", "content": prompt}]):
        full_response += chunk

    try:
        start = full_response.index("{")
        end = full_response.rindex("}") + 1
        parsed = json.loads(full_response[start:end])
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(500, "AI trả về định dạng không hợp lệ, thử lại.")

    part1, part2, part3 = parsed.get("part1", []), parsed.get("part2", []), parsed.get("part3", [])
    if not (part1 or part2 or part3):
        raise HTTPException(500, "AI không tạo được câu hỏi nào, thử lại.")

    exam = models.ExamPaper(
        subject_id=payload.subject_id,
        title=f"Đề thi thử {subject.name} — {len(part1) + len(part2) + len(part3)} câu",
        source_files=json.dumps(source_names, ensure_ascii=False),
        part1_count=len(part1), part2_count=len(part2), part3_count=len(part3),
    )
    db.add(exam)
    db.flush()

    order = 0
    for item in part1:
        q = models.Question(subject_id=payload.subject_id, content=item.get("content", ""),
                             question_type="mcq", source="ai_generated", explanation=item.get("explanation"))
        db.add(q); db.flush()
        for a in item.get("answers", []):
            db.add(models.Answer(question_id=q.id, content=a.get("content", ""), is_correct=a.get("is_correct", False)))
        db.add(models.ExamItem(exam_id=exam.id, question_id=q.id, part=1, order_index=order)); order += 1

    for item in part2:
        q = models.Question(subject_id=payload.subject_id, content=item.get("content", ""),
                             question_type="truefalse", source="ai_generated", explanation=item.get("explanation"))
        db.add(q); db.flush()
        for s in item.get("statements", []):
            db.add(models.Answer(question_id=q.id, content=s.get("content", ""), is_correct=s.get("is_correct", False)))
        db.add(models.ExamItem(exam_id=exam.id, question_id=q.id, part=2, order_index=order)); order += 1

    for item in part3:
        q = models.Question(subject_id=payload.subject_id, content=item.get("content", ""),
                             question_type="short_answer", source="ai_generated", explanation=item.get("explanation"),
                             correct_answer_text=item.get("correct_answer", ""))
        db.add(q); db.flush()
        db.add(models.ExamItem(exam_id=exam.id, question_id=q.id, part=3, order_index=order)); order += 1

    db.commit()
    db.refresh(exam)

    return schemas.ExamSummary(
        id=exam.id, title=exam.title, subject_id=exam.subject_id, created_at=exam.created_at,
        total_questions=len(part1) + len(part2) + len(part3), best_score=None,
    )


@router.get("/practice/exams", response_model=list[schemas.ExamSummary])
def list_exams(subject_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.ExamPaper)
    if subject_id:
        query = query.filter(models.ExamPaper.subject_id == subject_id)
    exams = query.order_by(models.ExamPaper.created_at.desc()).all()
    result = []
    for e in exams:
        best = max((a.score for a in e.attempts), default=None)
        result.append(schemas.ExamSummary(
            id=e.id, title=e.title, subject_id=e.subject_id, created_at=e.created_at,
            total_questions=e.part1_count + e.part2_count + e.part3_count,
            best_score=(best / 100) if best is not None else None,
        ))
    return result


@router.get("/practice/exams/{exam_id}", response_model=schemas.ExamOut)
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = (
        db.query(models.ExamPaper)
        .options(joinedload(models.ExamPaper.items).joinedload(models.ExamItem.question).joinedload(models.Question.answers))
        .get(exam_id)
    )
    if not exam:
        raise HTTPException(404, "Đề thi không tồn tại")

    def to_out(item):
        q = item.question
        answers = [schemas.AnswerOut(id=a.id, content=a.content, is_correct=False) for a in q.answers]
        return schemas.ExamQuestionOut(id=q.id, part=item.part, content=q.content, question_type=q.question_type, answers=answers)

    items_sorted = sorted(exam.items, key=lambda i: i.order_index)
    return schemas.ExamOut(
        id=exam.id, subject_id=exam.subject_id, title=exam.title,
        source_files=json.loads(exam.source_files) if exam.source_files else [],
        part1=[to_out(i) for i in items_sorted if i.part == 1],
        part2=[to_out(i) for i in items_sorted if i.part == 2],
        part3=[to_out(i) for i in items_sorted if i.part == 3],
    )


@router.delete("/practice/exams/{exam_id}")
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.ExamPaper).get(exam_id)
    if not exam:
        raise HTTPException(404, "Đề thi không tồn tại")
    db.delete(exam)
    db.commit()
    return {"ok": True}


@router.post("/practice/exams/{exam_id}/submit", response_model=schemas.ExamSubmitResult)
def submit_exam(exam_id: int, payload: schemas.ExamSubmitRequest, db: Session = Depends(get_db)):
    exam = (
        db.query(models.ExamPaper)
        .options(joinedload(models.ExamPaper.items).joinedload(models.ExamItem.question).joinedload(models.Question.answers))
        .get(exam_id)
    )
    if not exam:
        raise HTTPException(404, "Đề thi không tồn tại")

    p1_items = [i for i in exam.items if i.part == 1]
    p2_items = [i for i in exam.items if i.part == 2]
    p3_items = [i for i in exam.items if i.part == 3]

    # Thang điểm chuẩn THPT: Phần I = 3đ, Phần II = 4đ, Phần III = 3đ (chia đều cho số câu mỗi phần)
    p1_each = 3.0 / max(len(p1_items), 1)
    p2_each_max = 4.0 / max(len(p2_items), 1)
    p3_each = 3.0 / max(len(p3_items), 1)
    ratio_by_correct_count = {0: 0.0, 1: 0.1, 2: 0.25, 3: 0.5, 4: 1.0}

    details = []
    total_p1 = total_p2 = total_p3 = 0.0

    for item in p1_items:
        q = item.question
        correct = next((a for a in q.answers if a.is_correct), None)
        chosen_id = payload.mcq_answers.get(q.id)
        is_correct = bool(correct and chosen_id == correct.id)
        earned = p1_each if is_correct else 0.0
        total_p1 += earned
        details.append(schemas.ExamResultItem(
            question_id=q.id, part=1, is_correct=is_correct, earned_points=round(earned, 2),
            max_points=round(p1_each, 2), correct_display=correct.content if correct else "", explanation=q.explanation,
        ))

    for item in p2_items:
        q = item.question
        user_map = payload.truefalse_answers.get(q.id, {})
        n_correct = sum(
            1 for a in q.answers
            if user_map.get(a.id) is not None and bool(user_map.get(a.id)) == a.is_correct
        )
        ratio = ratio_by_correct_count.get(n_correct, 0.0)
        earned = p2_each_max * ratio
        total_p2 += earned
        correct_display = " · ".join(f"{a.content} → {'Đúng' if a.is_correct else 'Sai'}" for a in q.answers)
        details.append(schemas.ExamResultItem(
            question_id=q.id, part=2, is_correct=(n_correct == len(q.answers)), earned_points=round(earned, 2),
            max_points=round(p2_each_max, 2), correct_display=correct_display, explanation=q.explanation,
        ))

    for item in p3_items:
        q = item.question
        user_text = (payload.short_answers.get(q.id) or "").strip().lower()
        correct_text = (q.correct_answer_text or "").strip().lower()
        is_correct = bool(correct_text) and user_text == correct_text
        earned = p3_each if is_correct else 0.0
        total_p3 += earned
        details.append(schemas.ExamResultItem(
            question_id=q.id, part=3, is_correct=is_correct, earned_points=round(earned, 2),
            max_points=round(p3_each, 2), correct_display=q.correct_answer_text or "", explanation=q.explanation,
        ))

    total = round(total_p1 + total_p2 + total_p3, 2)

    for d in details:
        db.add(models.StudyHistory(question_id=d.question_id, is_correct=bool(d.is_correct)))

    db.add(models.ExamAttempt(
        exam_id=exam.id, score=int(total * 100),
        part1_score=int(total_p1 * 100), part2_score=int(total_p2 * 100), part3_score=int(total_p3 * 100),
        detail_json=json.dumps([d.model_dump() for d in details], ensure_ascii=False),
    ))
    db.commit()

    return schemas.ExamSubmitResult(
        total_score=total, part1_score=round(total_p1, 2), part2_score=round(total_p2, 2),
        part3_score=round(total_p3, 2), details=details,
    )


# ======================================================================
# Sổ lỗi sai / Thống kê — giữ nguyên logic cũ
# ======================================================================
@router.get("/practice/mistakes", response_model=list[schemas.QuestionOut])
def get_mistake_book(subject_id: int | None = None, db: Session = Depends(get_db)):
    wrong_ids_subq = (
        db.query(models.StudyHistory.question_id)
        .filter(models.StudyHistory.is_correct == False)  # noqa: E712
        .distinct()
        .subquery()
    )
    correct_ids_subq = (
        db.query(models.StudyHistory.question_id)
        .filter(models.StudyHistory.is_correct == True)  # noqa: E712
        .distinct()
        .subquery()
    )
    wrong_question_ids = [row[0] for row in db.query(wrong_ids_subq)]
    correct_question_ids = {row[0] for row in db.query(correct_ids_subq)}
    still_wrong_ids = [qid for qid in wrong_question_ids if qid not in correct_question_ids]

    query = (
        db.query(models.Question)
        .options(joinedload(models.Question.answers))
        .filter(models.Question.id.in_(still_wrong_ids))
    )
    if subject_id:
        query = query.filter(models.Question.subject_id == subject_id)

    questions = query.all()
    return [
        schemas.QuestionOut(
            id=q.id, subject_id=q.subject_id, content=q.content, question_type=q.question_type,
            difficulty=q.difficulty, source=q.source, explanation=q.explanation,
            answers=[schemas.AnswerOut(id=a.id, content=a.content, is_correct=a.is_correct) for a in q.answers],
        )
        for q in questions
    ]


@router.get("/practice/stats")
def get_practice_stats(db: Session = Depends(get_db)):
    subjects = db.query(models.Subject).all()
    stats = []
    for s in subjects:
        total = (
            db.query(models.StudyHistory)
            .join(models.Question)
            .filter(models.Question.subject_id == s.id)
            .count()
        )
        correct = (
            db.query(models.StudyHistory)
            .join(models.Question)
            .filter(models.Question.subject_id == s.id, models.StudyHistory.is_correct == True)  # noqa: E712
            .count()
        )
        stats.append({
            "subject_id": s.id, "subject_name": s.name,
            "total_attempts": total, "correct": correct,
            "percent_correct": round(correct / total * 100) if total else 0,
        })
    return stats