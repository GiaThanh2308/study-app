"""Unified, review-first intake for web and user-provided exam sources."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.catalog import EXAM_CATEGORIES
from app.core.database import DATA_DIR, get_db
from app.models.domain import (
    DuplicateCandidate,
    Exam,
    ExamQuestionLink,
    Question,
    SourceRecord,
    StagedExam,
    Subject,
    Topic,
)
from app.services.ingestion import (
    FINGERPRINT_VERSION,
    IngestionError,
    _question_fingerprint,
    _sha256,
    download_public_source,
    normalize_text_for_fingerprint,
    parse_questions,
    stage_source,
)


router = APIRouter()


class IntakeMetadata(BaseModel):
    subject_id: int
    title: str = Field(min_length=2, max_length=300)
    category: str
    exam_year: int | None = Field(default=None, ge=2000, le=2100)
    semester: str | None = Field(default=None, max_length=16)
    exam_month: int | None = Field(default=None, ge=1, le=12)
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    province: str | None = Field(default=None, max_length=120)
    school_name: str | None = Field(default=None, max_length=240)


class TextIntake(IntakeMetadata):
    text: str = Field(min_length=1, max_length=2_000_000)


class StageUpdate(BaseModel):
    metadata: dict[str, Any] | None = None
    questions: list[dict[str, Any]] | None = None


class PublishRequest(BaseModel):
    provenance_status: str = "unverified"
    allow_similar_duplicate: bool = False


class VerifyAnswerRequest(BaseModel):
    position: int = Field(ge=1)
    answer: Any


def _http_error(exc: IngestionError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _validate_metadata(db: Session, metadata: IntakeMetadata) -> dict[str, Any]:
    if metadata.category not in EXAM_CATEGORIES - {"generated"}:
        raise HTTPException(status_code=422, detail="Loại đề nhập từ nguồn phải là đề có sẵn, không phải đề AI tạo.")
    if not db.get(Subject, metadata.subject_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học.")
    result = metadata.model_dump(exclude={"text"}, exclude_none=True)
    result["title"] = result["title"].strip()
    for key in ("semester", "province", "school_name"):
        if key in result and isinstance(result[key], str):
            result[key] = result[key].strip() or None
    return result


def _stage_payload(stage: StagedExam, db: Session, *, include_text: bool = True) -> dict[str, Any]:
    source = stage.source_record
    candidates = db.scalars(
        select(DuplicateCandidate).where(
            DuplicateCandidate.left_kind == "source_record",
            DuplicateCandidate.left_id == source.id,
        )
    ).all() if source else []
    duplicate_details = []
    for candidate in candidates:
        right_title = None
        if candidate.right_kind == "exam":
            right_title = db.scalar(select(Exam.title).where(Exam.id == candidate.right_id))
        elif candidate.right_kind == "source_record":
            right_title = db.scalar(select(Exam.title).join(SourceRecord).where(SourceRecord.id == candidate.right_id))
        duplicate_details.append({"match_kind": candidate.match_kind, "similarity": candidate.similarity,
                                  "status": candidate.status, "exam_title": right_title})
    return {
        "id": stage.id,
        "status": stage.status,
        "created_at": stage.created_at.isoformat() if stage.created_at else None,
        "metadata": (stage.extracted_data or {}).get("metadata", {}),
        "questions": (stage.extracted_data or {}).get("questions", []),
        "warnings": stage.warnings or [],
        "raw_payload": (stage.raw_payload or "") if include_text else None,
        "source": {
            "source_kind": source.source_kind,
            "source_url": source.source_url,
            "original_filename": source.original_filename,
            "sha256": source.sha256,
            "raw_url": f"/data/{source.raw_file_path}" if source.raw_file_path else None,
        } if source else None,
        "duplicates": duplicate_details,
    }


async def _stage(db: Session, *, data: bytes, filename: str | None, content_type: str,
                 source_kind: str, source_url: str | None, input_reference: str,
                 metadata: dict[str, Any], raw_text_override: str | None = None) -> dict[str, Any]:
    try:
        stage = await stage_source(db, data=data, filename=filename, content_type=content_type,
                                   source_kind=source_kind, source_url=source_url,
                                   input_reference=input_reference, metadata=metadata,
                                   raw_text_override=raw_text_override)
    except IngestionError as exc:
        raise _http_error(exc) from exc
    return _stage_payload(stage, db)


@router.post("/imports/url")
async def import_url(url: str = Form(...), metadata: str = Form(...), db: Session = Depends(get_db)):
    try:
        values = IntakeMetadata.model_validate_json(metadata)
        clean = _validate_metadata(db, values)
        data, filename, content_type, final_url = await download_public_source(url)
        return await _stage(db, data=data, filename=filename, content_type=content_type,
                            source_kind="web", source_url=final_url, input_reference=url,
                            metadata=clean)
    except IngestionError as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Metadata không hợp lệ.") from exc


@router.post("/imports/file")
async def import_file(file: UploadFile = File(...), metadata: str = Form(...), db: Session = Depends(get_db)):
    try:
        values = IntakeMetadata.model_validate_json(metadata)
        clean = _validate_metadata(db, values)
        data = await file.read(20 * 1024 * 1024 + 1)
        return await _stage(db, data=data, filename=file.filename, content_type=file.content_type or "application/octet-stream",
                            source_kind="user_import", source_url=None,
                            input_reference=file.filename or "upload", metadata=clean)
    except IngestionError as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Metadata không hợp lệ.") from exc


@router.post("/imports/text")
async def import_text(payload: TextIntake, db: Session = Depends(get_db)):
    clean = _validate_metadata(db, payload)
    text = payload.text
    data = text.encode("utf-8")
    return await _stage(db, data=data, filename="pasted-exam.txt", content_type="text/plain; charset=utf-8",
                        source_kind="user_import", source_url=None, input_reference="pasted text",
                        metadata=clean, raw_text_override=text)


@router.get("/imports/staged")
def list_staged(db: Session = Depends(get_db)):
    rows = db.scalars(select(StagedExam).where(StagedExam.status == "needs_review")
                      .options(joinedload(StagedExam.source_record)).order_by(StagedExam.created_at.desc())).all()
    return [_stage_payload(row, db, include_text=False) for row in rows]


@router.get("/imports/staged/{stage_id}")
def get_staged(stage_id: int, db: Session = Depends(get_db)):
    stage = db.scalar(select(StagedExam).where(StagedExam.id == stage_id).options(joinedload(StagedExam.source_record)))
    if not stage:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản nhập chờ duyệt.")
    return _stage_payload(stage, db)


@router.patch("/imports/staged/{stage_id}")
def update_staged(stage_id: int, payload: StageUpdate, db: Session = Depends(get_db)):
    stage = db.scalar(select(StagedExam).where(StagedExam.id == stage_id).options(joinedload(StagedExam.source_record)))
    if not stage or stage.status != "needs_review":
        raise HTTPException(status_code=404, detail="Không tìm thấy bản nhập có thể chỉnh sửa.")
    data = dict(stage.extracted_data or {})
    if payload.metadata is not None:
        try:
            values = IntakeMetadata.model_validate(payload.metadata)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Metadata không hợp lệ.") from exc
        data["metadata"] = _validate_metadata(db, values)
    if payload.questions is not None:
        if stage.source_record.source_kind == "web":
            raise HTTPException(status_code=403, detail="Câu hỏi trích từ đề web được khóa để giữ nguyên nội dung nguồn.")
        if len(payload.questions) > 1000:
            raise HTTPException(status_code=422, detail="Một đề không thể có quá 1000 câu.")
        subject_id = data.get("metadata", {}).get("subject_id")
        for position, item in enumerate(payload.questions, 1):
            if not isinstance(item, dict) or not str(item.get("content", "")).strip():
                raise HTTPException(status_code=422, detail=f"Câu {position} thiếu nội dung.")
            item["position"] = position
            item["answer_status"] = "verified" if item.get("answer_status") == "verified" and item.get("candidate_answer") is not None else "unknown"
            topic_id = item.get("topic_id")
            if topic_id and not db.scalar(select(Topic.id).where(Topic.id == topic_id, Topic.subject_id == subject_id)):
                raise HTTPException(status_code=422, detail=f"Chủ đề của câu {position} không thuộc môn đã chọn.")
        data["questions"] = payload.questions
    stage.extracted_data = data
    db.commit()
    db.refresh(stage)
    return _stage_payload(stage, db)


@router.post("/imports/staged/{stage_id}/publish")
def publish_staged(stage_id: int, payload: PublishRequest, db: Session = Depends(get_db)):
    stage = db.scalar(select(StagedExam).where(StagedExam.id == stage_id)
                      .options(joinedload(StagedExam.source_record), selectinload(StagedExam.job)))
    if not stage or stage.status != "needs_review":
        raise HTTPException(status_code=404, detail="Không tìm thấy bản nhập có thể xuất bản.")
    data = dict(stage.extracted_data or {})
    metadata = data.get("metadata", {})
    try:
        clean = _validate_metadata(db, IntakeMetadata.model_validate(metadata))
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=422, detail="Metadata đề chưa đầy đủ.") from exc
    if payload.provenance_status not in {"unverified", "source_verified", "reviewed"}:
        raise HTTPException(status_code=422, detail="Trạng thái xác minh nguồn không hợp lệ.")
    source = stage.source_record

    # Exact same bytes already published: attach provenance to the existing exam, never clone it.
    exact = db.scalar(select(Exam).join(SourceRecord).where(
        SourceRecord.sha256 == source.sha256, Exam.status == "published",
        Exam.subject_id == clean["subject_id"], Exam.category == clean["category"],
    ))
    if exact is None and source.content_fingerprint:
        exact = db.scalar(select(Exam).join(SourceRecord).where(
            SourceRecord.content_fingerprint == source.content_fingerprint, Exam.status == "published",
            Exam.subject_id == clean["subject_id"], Exam.category == clean["category"],
        ))
    if exact:
        source.exam_id = exact.id
        stage.status = "duplicate_linked"
        stage.job.status = "completed"
        db.commit()
        return {"status": "duplicate_linked", "exam_id": exact.id, "title": exact.title}

    pending = db.scalars(select(DuplicateCandidate).where(
        DuplicateCandidate.left_kind == "source_record", DuplicateCandidate.left_id == source.id,
        DuplicateCandidate.status == "pending")).all()
    similar = [item for item in pending if item.match_kind != "exact_file"]
    if similar and not payload.allow_similar_duplicate:
        raise HTTPException(status_code=409, detail={
            "message": "Có nguồn trùng nội dung hoặc gần trùng. Hãy xem cảnh báo và xác nhận nếu vẫn muốn lưu thành đề riêng.",
            "duplicates": _stage_payload(stage, db)["duplicates"],
        })
    for candidate in pending:
        candidate.status = "allowed_separate" if payload.allow_similar_duplicate else "exact_linked"

    questions = data.get("questions", [])
    exam_fingerprint_data = {
        "subject_id": clean["subject_id"], "category": clean["category"],
        "questions": [item.get("fingerprint") or _question_fingerprint(item.get("question_type", "unknown"),
                      item.get("content", ""), item.get("options"), item.get("candidate_answer")) for item in questions],
    }
    import hashlib
    fingerprint = hashlib.sha256(json.dumps(exam_fingerprint_data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    exam = Exam(subject_id=clean["subject_id"], title=clean["title"], category=clean["category"], status="published",
                provenance_status=payload.provenance_status, max_score=10.0, scoring_config={},
                exam_year=clean.get("exam_year"), semester=clean.get("semester"), exam_month=clean.get("exam_month"),
                duration_minutes=clean.get("duration_minutes"), province=clean.get("province"), school_name=clean.get("school_name"),
                total_questions=len(questions), fingerprint=fingerprint, fingerprint_version=FINGERPRINT_VERSION)
    db.add(exam)
    db.flush()
    for position, item in enumerate(questions, 1):
        content = str(item.get("content", "")).strip()
        candidate_answer = item.get("candidate_answer")
        verified = item.get("answer_status") == "verified" and candidate_answer is not None
        question = Question(subject_id=exam.subject_id, topic_id=item.get("topic_id"),
                            question_type=item.get("question_type") or "unknown", content=content,
                            options=item.get("options"), answer=candidate_answer if verified else None,
                            answer_status="verified" if verified else "unknown", explanation=item.get("explanation"),
                            difficulty=item.get("difficulty"), cognitive_level=item.get("cognitive_level"),
                            fingerprint=_question_fingerprint(item.get("question_type") or "unknown", content,
                                                              item.get("options"), candidate_answer if verified else None),
                            fingerprint_version=FINGERPRINT_VERSION, content_origin=source.source_kind)
        db.add(question)
        db.flush()
        db.add(ExamQuestionLink(exam_id=exam.id, question_id=question.id,
                                position=int(item.get("position", position)), points=item.get("points")))
        db.add(SourceRecord(exam_id=exam.id, question_id=question.id, source_kind=source.source_kind,
                            source_url=source.source_url, original_filename=source.original_filename,
                            sha256=source.sha256, content_fingerprint=source.content_fingerprint,
                            fingerprint_version=source.fingerprint_version, raw_file_path=source.raw_file_path,
                            metadata_json={"derived_from_source_record_id": source.id}))
    source.exam_id = exam.id
    stage.status = "published"
    stage.job.status = "completed"
    db.commit()
    return {"status": "published", "exam_id": exam.id, "title": exam.title,
            "question_count": len(questions), "can_practice": bool(questions) and all(
                item.get("answer_status") == "verified" and item.get("candidate_answer") is not None for item in questions)}


@router.post("/imports/staged/{stage_id}/reject")
def reject_staged(stage_id: int, db: Session = Depends(get_db)):
    stage = db.get(StagedExam, stage_id)
    if not stage or stage.status != "needs_review":
        raise HTTPException(status_code=404, detail="Không tìm thấy bản nhập có thể từ chối.")
    stage.status = "rejected"
    job = stage.job
    job.status = "rejected"
    db.commit()
    return {"status": "rejected", "stage_id": stage.id}


@router.post("/imports/staged/{stage_id}/verify-answer")
def verify_answer(stage_id: int, payload: VerifyAnswerRequest, db: Session = Depends(get_db)):
    stage = db.scalar(select(StagedExam).where(StagedExam.id == stage_id).options(joinedload(StagedExam.source_record)))
    if not stage or stage.status != "needs_review":
        raise HTTPException(status_code=404, detail="Không tìm thấy bản nhập có thể xác minh.")
    data = dict(stage.extracted_data or {})
    questions = list(data.get("questions", []))
    if payload.position > len(questions):
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi tại vị trí này.")
    question = dict(questions[payload.position - 1])
    if not str(question.get("content", "")).strip():
        raise HTTPException(status_code=422, detail="Câu hỏi cần được trích xuất trước khi xác minh đáp án.")
    question["candidate_answer"] = payload.answer
    question["answer_status"] = "verified"
    questions[payload.position - 1] = question
    data["questions"] = questions
    stage.extracted_data = data
    db.commit()
    db.refresh(stage)
    return _stage_payload(stage, db)
