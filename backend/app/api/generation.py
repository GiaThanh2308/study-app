"""Local, serialized generation jobs and answer-review lifecycle."""

import asyncio
import logging
import threading
from typing import Any
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.ai.gemini_client import GEMINI_MODEL, is_gemini_configured
from app.core.database import SessionLocal, get_db
from app.models.domain import BlueprintVersion, Exam, ExamQuestionLink, GenerationJob, Question, SourceRecord, Subject, Topic
from app.services.generation import (
    PROMPT_VERSION, GenerationError, build_allocations, exam_fingerprint,
    existing_question_fingerprints, generate_section, get_active_blueprint, largest_remainder, validate_section_output,
)
from app.services.ingestion import FINGERPRINT_VERSION, _question_fingerprint


router = APIRouter()
logger = logging.getLogger("studyapp.generation")
_worker_lock = asyncio.Lock()
_start_lock = threading.Lock()
_ACTIVE = {"queued", "running"}


class StartGeneration(BaseModel):
    subject_slug: str = Field(pattern="^(toan|vat-ly|hoa-hoc)$")
    mode: str = Field(default="full", pattern="^(full|focused)$")
    title: str | None = Field(default=None, max_length=300)
    difficulty: dict[str, int] = Field(default_factory=lambda: {"easy": 30, "medium": 50, "hard": 20})
    section_names: list[str] = Field(default_factory=list)
    topic_ids: list[int] = Field(default_factory=list)
    questions_per_section: int = Field(default=5, ge=1, le=20)


class QuestionEdit(BaseModel):
    content: str | None = Field(default=None, min_length=12, max_length=12000)
    options: dict[str, str] | None = None
    answer: Any = None
    explanation: str | None = Field(default=None, min_length=15, max_length=6000)
    confirm: bool = False


def _job_payload(job: GenerationJob) -> dict[str, Any]:
    progress = job.progress_json or {}
    return {"id": job.id, "status": job.status, "model": job.model_name,
            "prompt_version": job.prompt_version, "progress": progress,
            "error": job.error_message, "result_exam_id": job.result_exam_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "cancel_requested": job.cancel_requested}


@router.get("/generation/blueprints")
def generation_blueprints(db: Session = Depends(get_db)):
    result = []
    for slug in ("toan", "vat-ly", "hoa-hoc"):
        try:
            subject, version, rules, topics = get_active_blueprint(db, slug)
        except GenerationError:
            continue
        result.append({"slug": slug, "name": subject.name, "icon": subject.icon,
                       "blueprint_version_id": version.id, "version": version.version,
                       "duration_minutes": rules["duration_minutes"], "question_count": rules["question_count"],
                       "prompt_count": rules["prompt_count"],
                       "sections": [{"name": section["name"], "type": section["type"],
                                     "questions": section["questions"]} for section in rules["sections"]],
                       "topics": [{"id": topic.id, "name": topic.name, "grade": topic.grade} for topic in topics]})
    return {"gemini_configured": is_gemini_configured(), "model": GEMINI_MODEL, "subjects": result}


@router.get("/generation-jobs")
def list_generation_jobs(limit: int = 20, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 50)
    rows = db.scalars(select(GenerationJob).order_by(GenerationJob.created_at.desc(), GenerationJob.id.desc()).limit(limit)).all()
    return [_job_payload(job) for job in rows]


def _prepare_request(db: Session, payload: StartGeneration) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    subject, version, rules, topics = get_active_blueprint(db, payload.subject_slug)
    all_allocations = build_allocations(rules, payload.difficulty, topics)
    sections = all_allocations["sections"]
    if payload.mode == "focused":
        if not payload.section_names or not payload.topic_ids:
            raise GenerationError("Bộ câu hỏi theo chủ đề cần chọn ít nhất một phần và một chủ đề.")
        if len(payload.section_names) != len(set(payload.section_names)):
            raise GenerationError("Không chọn lặp lại cùng một phần thi.")
        selected = set(payload.topic_ids)
        valid_topic_ids = {topic.id for topic in topics}
        if not selected <= valid_topic_ids:
            raise GenerationError("Có chủ đề không thuộc môn đã chọn.")
        section_map = {section["name"]: section for section in sections}
        if not set(payload.section_names) <= set(section_map):
            raise GenerationError("Có phần thi không thuộc ma trận.")
        focused_sections = []
        scoped_topics = [topic for topic in topics if topic.id in selected]
        eligible = [topic for topic in scoped_topics if str(topic.grade) in rules["topics"]]
        if not eligible:
            raise GenerationError("Không có chủ đề hợp lệ trong lựa chọn.")
        total_units = sum(payload.questions_per_section * (4 if section_map[name]["type"] == "true_false" else 1)
                          for name in payload.section_names)
        cognitive_counts = largest_remainder(total_units, rules["cognitive_weight_percent"])
        difficulty_counts = largest_remainder(total_units, payload.difficulty)
        grade_counts = largest_remainder(total_units, {str(grade): 1 for grade in sorted({topic.grade for topic in eligible})})
        units = [{} for _ in range(total_units)]
        for field, counts in (("grade", grade_counts), ("cognitive_level", cognitive_counts), ("difficulty", difficulty_counts)):
            values = [value for value, amount in counts.items() for _ in range(amount)]
            for index, value in enumerate(values):
                units[index][field] = int(value) if field == "grade" else value
        eligible_by_grade: dict[int, list[Topic]] = {}
        for topic in eligible:
            eligible_by_grade.setdefault(topic.grade, []).append(topic)
        topic_counts: dict[int, int] = {}
        for unit in units:
            matches = sorted(eligible_by_grade[unit["grade"]], key=lambda item: item.id)
            index = topic_counts.get(unit["grade"], 0)
            chosen = matches[index % len(matches)]
            topic_counts[unit["grade"]] = index + 1
            unit.update({"topic_id": chosen.id, "topic": chosen.name})
        cursor = 0
        for name in payload.section_names:
            template = section_map[name]
            unit_count = payload.questions_per_section * (4 if template["type"] == "true_false" else 1)
            focused_sections.append({**template, "questions": payload.questions_per_section,
                                     "allocations": units[cursor:cursor + unit_count]})
            cursor += unit_count
        allocation = {**all_allocations, "sections": focused_sections,
                      "question_count": sum(item["questions"] for item in focused_sections),
                      "prompt_count": sum(len(item["allocations"]) for item in focused_sections),
                      "allocations": [unit for section in focused_sections for unit in section["allocations"]],
                      "duration_minutes": max(5, round(int(rules["duration_minutes"]) *
                          sum(item["questions"] for item in focused_sections) / int(rules["question_count"])))}
    else:
        allocation = all_allocations
    raw_max = sum(section["questions"] * (1.0 if section["type"] == "true_false"
                    else float(section.get("points_per_question") or 0)) for section in allocation["sections"])
    allocation["points_scale"] = 10.0 / raw_max if payload.mode == "focused" and raw_max > 0 else 1.0
    request = {"subject_slug": subject.slug, "mode": payload.mode,
               "title": (payload.title or "").strip() or f"Đề luyện {subject.name} theo ma trận {version.version}",
               "difficulty": payload.difficulty, "section_names": [s["name"] for s in allocation["sections"]],
               "topic_ids": payload.topic_ids if payload.mode == "focused" else [],
               "allocation": allocation}
    return subject, version, rules, request


async def _run_job(job_id: int) -> None:
    async with _worker_lock:
        with SessionLocal() as db:
            job = db.get(GenerationJob, job_id)
            if not job or job.status not in {"queued", "interrupted"}:
                return
            request = job.request_data
            version = db.get(BlueprintVersion, job.blueprint_version_id)
            if version is None:
                job.status = "failed"
                job.error_message = "Không tìm thấy phiên bản ma trận của job."
                db.commit()
                return
            rules = version.rules
            blueprint = version.blueprint
            subject = db.get(Subject, blueprint.subject_id)
            if subject is None:
                job.status = "failed"
                job.error_message = "Không tìm thấy môn học của job."
                db.commit()
                return
            subject = SimpleNamespace(id=subject.id, name=subject.name)
            version_id = version.id
            version_source_sha256 = version.source_sha256
            job.status = "running"
            job.error_message = None
            db.commit()
        try:
            for index, section in enumerate(request["allocation"]["sections"]):
                with SessionLocal() as db:
                    job = db.get(GenerationJob, job_id)
                    if job is None:
                        return
                    completed = (job.output_data or {}).get("sections", {})
                    if job.cancel_requested:
                        job.status = "cancelled"
                        job.progress_json = {"current_section": section["name"], "completed": len(completed),
                                             "total": len(request["allocation"]["sections"])}
                        db.commit()
                        return
                    if section["name"] in completed:
                        continue
                    job.progress_json = {"current_section": section["name"], "completed": len(completed),
                                         "total": len(request["allocation"]["sections"]), "section_index": index + 1}
                    db.commit()
                section_rules = rules
                if request["mode"] == "focused":
                    allowed = {str(unit["grade"]): [] for unit in section["allocations"]}
                    for unit in section["allocations"]:
                        if unit["topic"] not in allowed[str(unit["grade"])]:
                            allowed[str(unit["grade"])].append(unit["topic"])
                    section_rules = {**rules, "topics": allowed}
                raw = await generate_section(subject, section_rules, section, mode=request["mode"])
                with SessionLocal() as db:
                    job = db.get(GenerationJob, job_id)
                    if job is None:
                        return
                    existing = existing_question_fingerprints(db, subject.id)
                    for saved in (job.output_data or {}).get("sections", {}).values():
                        existing.update(question["fingerprint"] for question in saved)
                    validated = validate_section_output(section, raw, existing_fingerprints=existing)
                    data = dict(job.output_data or {"sections": {}})
                    complete = dict(data.get("sections", {}))
                    complete[section["name"]] = validated
                    data["sections"] = complete
                    job.output_data = data
                    job.progress_json = {"current_section": section["name"], "completed": len(complete),
                                         "total": len(request["allocation"]["sections"]),
                                         "counts": {"question_groups": sum(len(x) for x in complete.values())}}
                    db.commit()

            with SessionLocal.begin() as db:
                job = db.get(GenerationJob, job_id)
                data = job.output_data or {}
                questions = [question for section in request["allocation"]["sections"]
                             for question in data.get("sections", {}).get(section["name"], [])]
                expected = request["allocation"]["question_count"]
                if len(questions) != expected:
                    raise GenerationError("Đầu ra chưa đủ số câu; bản đề không được tạo.")
                exam = Exam(subject_id=subject.id, blueprint_version_id=version_id,
                            title=request["title"], category="generated", status="draft",
                            provenance_status="unverified", max_score=10.0,
                            scoring_config={"true_false_correct_items": next((s["scoring_per_correct_item_count"]
                                for s in rules["sections"] if s["type"] == "true_false"), {"1": 0.1, "2": 0.25, "3": 0.5, "4": 1.0})},
                            duration_minutes=request["allocation"]["duration_minutes"],
                            total_questions=len(questions), fingerprint=exam_fingerprint(questions), fingerprint_version=FINGERPRINT_VERSION)
                db.add(exam)
                db.flush()
                position = 0
                for section in request["allocation"]["sections"]:
                    for value in data["sections"][section["name"]]:
                        position += 1
                        question = Question(subject_id=subject.id, topic_id=value["topic_id"],
                                            question_type=value["question_type"], content=value["content"],
                                            options=value["options"], answer=value["answer"], answer_status="unknown",
                                            explanation=value["explanation"], difficulty=value["difficulty"],
                                            cognitive_level=value["cognitive_level"], assessment_breakdown=value["assessment_breakdown"],
                                            fingerprint=value["fingerprint"], fingerprint_version=FINGERPRINT_VERSION,
                                            content_origin="generated")
                        db.add(question)
                        db.flush()
                        points = (1.0 if section["type"] == "true_false" else float(section.get("points_per_question") or 0)) * float(request["allocation"].get("points_scale", 1.0))
                        db.add(ExamQuestionLink(exam_id=exam.id, question_id=question.id, position=position,
                                                section=section["name"], points=points))
                db.add(SourceRecord(exam_id=exam.id, source_kind="generated", metadata_json={
                    "generation_job_id": job.id, "model": job.model_name, "prompt_version": job.prompt_version,
                    "blueprint_version_id": version_id, "blueprint_source_sha256": version_source_sha256,
                    "mode": request["mode"], "difficulty": request["difficulty"]}))
                job.result_exam_id = exam.id
                job.status = "completed_awaiting_review"
                job.progress_json = {"completed": len(request["allocation"]["sections"]),
                                     "total": len(request["allocation"]["sections"]),
                                     "question_groups": len(questions), "scored_prompts": request["allocation"]["prompt_count"]}
        except Exception as exc:
            logger.error("Generation job failed unexpectedly: job_id=%s type=%s", job_id, type(exc).__name__)
            with SessionLocal.begin() as db:
                job = db.get(GenerationJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000] if isinstance(exc, GenerationError) else "Gemini không hoàn tất được phần này. Các phần đã kiểm tra vẫn được giữ để tiếp tục thủ công."


@router.post("/generation-jobs", status_code=202)
def start_generation(payload: StartGeneration, background: BackgroundTasks, db: Session = Depends(get_db)):
    if not is_gemini_configured():
        raise HTTPException(status_code=503, detail="Chưa cấu hình GEMINI_API_KEY trong backend/.env. Không có dịch vụ trả phí dự phòng.")
    _start_lock.acquire()
    try:
        active = db.scalar(select(GenerationJob.id).where(GenerationJob.status.in_(_ACTIVE)).limit(1))
        if active is not None:
            raise HTTPException(status_code=409, detail="Đang có một job tạo đề chạy; hãy chờ hoặc hủy job đó trước.")
        subject, version, _, request = _prepare_request(db, payload)
        job = GenerationJob(blueprint_version_id=version.id, status="queued", request_data=request,
                            progress_json={"completed": 0, "total": len(request["allocation"]["sections"])},
                            output_data={"sections": {}}, model_name=GEMINI_MODEL, prompt_version=PROMPT_VERSION)
        db.add(job)
        db.commit()
        db.refresh(job)
    except GenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        _start_lock.release()
    background.add_task(_run_job, job.id)
    return _job_payload(job)


@router.get("/generation-jobs/{job_id}")
def get_generation_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job tạo đề.")
    return _job_payload(job)


@router.post("/generation-jobs/{job_id}/cancel")
def cancel_generation(job_id: int, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job or job.status not in _ACTIVE:
        raise HTTPException(status_code=409, detail="Job không ở trạng thái có thể hủy.")
    job.cancel_requested = True
    db.commit()
    return _job_payload(job)


@router.post("/generation-jobs/{job_id}/resume", status_code=202)
def resume_generation(job_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job or job.status not in {"failed", "interrupted", "cancelled"}:
        raise HTTPException(status_code=409, detail="Job không ở trạng thái có thể tiếp tục.")
    _start_lock.acquire()
    try:
        active = db.scalar(select(GenerationJob.id).where(GenerationJob.status.in_(_ACTIVE)).limit(1))
        if active:
            raise HTTPException(status_code=409, detail="Đang có một job tạo đề khác.")
        job.status = "queued"
        job.cancel_requested = False
        job.error_message = None
        db.commit()
    finally:
        _start_lock.release()
    background.add_task(_run_job, job.id)
    return _job_payload(job)


def _review_data(exam: Exam, job: GenerationJob) -> dict[str, Any]:
    allocations = (job.request_data.get("allocation") or {}).get("allocations", [])
    targets = {key: {} for key in ("grade", "cognitive_level", "difficulty")}
    for unit in allocations:
        for key in targets:
            value = str(unit[key])
            targets[key][value] = targets[key].get(value, 0) + 1
    return {"exam": {"id": exam.id, "title": exam.title, "status": exam.status,
                      "duration_minutes": exam.duration_minutes, "max_score": exam.max_score,
                      "total_questions": exam.total_questions}, "targets": targets,
            "questions": [{"position": link.position, "id": link.question.id,
                           "question_type": link.question.question_type, "content": link.question.content,
                           "options": link.question.options, "answer": link.question.answer,
                           "explanation": link.question.explanation, "answer_status": link.question.answer_status,
                           "points": link.points, "assessment_breakdown": link.question.assessment_breakdown}
                          for link in exam.questions]}


def _get_job_exam(db: Session, job_id: int) -> tuple[GenerationJob, Exam]:
    job = db.get(GenerationJob, job_id)
    if not job or not job.result_exam_id:
        raise HTTPException(status_code=404, detail="Job chưa có bản đề để duyệt.")
    exam = db.scalar(select(Exam).where(Exam.id == job.result_exam_id).options(
        selectinload(Exam.questions).joinedload(ExamQuestionLink.question)))
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản đề.")
    return job, exam


def _reviewable_answer(question: Question) -> bool:
    answer = question.answer
    if question.question_type == "multiple_choice":
        return (isinstance(answer, str) and answer.upper() in {"A", "B", "C", "D"}
                and isinstance(question.options, dict)
                and {key.upper() for key in question.options} == {"A", "B", "C", "D"}
                and all(str(value).strip() for value in question.options.values())
                and len({str(value).strip().casefold() for value in question.options.values()}) == 4)
    if question.question_type == "true_false":
        return (isinstance(answer, list) and len(answer) == 4 and all(type(value) is bool for value in answer)
                and isinstance(question.options, dict) and set(question.options) == {"a", "b", "c", "d"}
                and all(str(value).strip() for value in question.options.values()))
    if question.question_type == "short_answer" and isinstance(answer, dict):
        try:
            accepted = answer.get("accepted")
            tolerance = Decimal(str(answer.get("tolerance", "0")))
            return (isinstance(accepted, list) and len(accepted) > 0
                    and all(Decimal(str(value)).is_finite() for value in accepted)
                    and tolerance.is_finite() and tolerance >= 0)
        except (InvalidOperation, TypeError, ValueError):
            return False
    return False


@router.get("/generation-jobs/{job_id}/review")
def review_generation(job_id: int, db: Session = Depends(get_db)):
    job, exam = _get_job_exam(db, job_id)
    return _review_data(exam, job)


@router.patch("/generation-jobs/{job_id}/questions/{position}")
def edit_generated_question(job_id: int, position: int, payload: QuestionEdit, db: Session = Depends(get_db)):
    job, exam = _get_job_exam(db, job_id)
    if exam.status != "draft":
        raise HTTPException(status_code=409, detail="Chỉ chỉnh sửa đề đang chờ duyệt.")
    link = next((item for item in exam.questions if item.position == position), None)
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    question = link.question
    changes = payload.model_dump(exclude_unset=True)
    confirm = changes.pop("confirm", False)
    if "content" in changes:
        question.content = changes["content"].strip()
    if "options" in changes:
        question.options = ({key.upper(): value for key, value in changes["options"].items()}
                            if question.question_type == "multiple_choice"
                            else {key.lower(): value for key, value in changes["options"].items()}
                            if question.question_type == "true_false" else changes["options"])
    if "answer" in changes:
        question.answer = (str(changes["answer"]).upper() if question.question_type == "multiple_choice"
                           and changes["answer"] is not None else changes["answer"])
    if "explanation" in changes:
        question.explanation = changes["explanation"].strip()
    question.fingerprint = _question_fingerprint(question.question_type, question.content, question.options, question.answer)
    question.fingerprint_version = FINGERPRINT_VERSION
    duplicate_id = db.scalar(select(Question.id).where(Question.subject_id == question.subject_id,
        Question.fingerprint == question.fingerprint, Question.id != question.id).limit(1))
    if duplicate_id:
        raise HTTPException(status_code=409, detail="Câu sau khi chỉnh sửa trùng với câu đã có trong ngân hàng.")
    if confirm:
        if not _reviewable_answer(question) or not question.explanation:
            raise HTTPException(status_code=422, detail="Đáp án không đúng định dạng chấm tự động hoặc thiếu lời giải.")
        question.answer_status = "verified"
    else:
        question.answer_status = "unknown"
    db.commit()
    return {"position": position, "answer_status": question.answer_status}


@router.post("/generation-jobs/{job_id}/confirm-all")
def confirm_all_generated_answers(job_id: int, db: Session = Depends(get_db)):
    _, exam = _get_job_exam(db, job_id)
    if exam.status != "draft" or not exam.questions:
        raise HTTPException(status_code=409, detail="Đề không ở trạng thái chờ duyệt.")
    if any(not _reviewable_answer(link.question) or not link.question.explanation for link in exam.questions):
        raise HTTPException(status_code=422, detail="Có câu có key sai định dạng hoặc thiếu lời giải.")
    for link in exam.questions:
        link.question.answer_status = "verified"
    db.commit()
    return {"verified": len(exam.questions)}


@router.post("/generation-jobs/{job_id}/publish")
def publish_generated_exam(job_id: int, db: Session = Depends(get_db)):
    job, exam = _get_job_exam(db, job_id)
    if exam.status != "draft" or not exam.questions:
        raise HTTPException(status_code=409, detail="Đề không ở trạng thái chờ duyệt.")
    if any(link.question.answer_status != "verified" or link.question.answer is None
           or link.question.question_type not in {"multiple_choice", "true_false", "short_answer"}
           for link in exam.questions):
        raise HTTPException(status_code=409, detail="Cần xác nhận đáp án cho mọi câu trước khi xuất bản.")
    exam.status = "published"
    exam.provenance_status = "reviewed"
    job.status = "published"
    db.commit()
    return {"exam_id": exam.id, "status": exam.status, "provenance_status": exam.provenance_status}


def mark_interrupted_jobs() -> int:
    with SessionLocal.begin() as db:
        jobs = db.scalars(select(GenerationJob).where(GenerationJob.status.in_({"queued", "running"}))).all()
        for job in jobs:
            job.status = "interrupted"
            job.error_message = "StudyApp đã đóng khi job còn chạy. Tiếp tục thủ công để gửi các phần chưa hoàn tất."
        return len(jobs)
