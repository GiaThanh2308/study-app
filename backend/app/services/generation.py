"""Blueprint-bound AI generation and deterministic output validation."""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClientError, generate_structured
from app.models.domain import Blueprint, BlueprintVersion, Question, Subject, Topic
from app.services.ingestion import FINGERPRINT_VERSION, _question_fingerprint


PROMPT_VERSION = "blueprint-v1"
SECTION_OUTPUT_TOKENS = 8192


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stem: str = Field(min_length=12, max_length=12000)
    options: dict[str, str] | None = None
    statements: list[str] | None = None
    answer_choice: str | None = None
    answer_true_false: list[bool] | None = None
    accepted_answers: list[str] | None = None
    tolerance: str | None = None
    explanation: str = Field(min_length=15, max_length=6000)


class SectionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[GeneratedQuestion]


class GenerationError(Exception):
    """Safe, deterministic generation/validation error."""


def largest_remainder(total: int, weights: dict[str, float]) -> dict[str, int]:
    if total < 0 or not weights or any(value < 0 for value in weights.values()):
        raise GenerationError("Tỷ lệ phân bổ không hợp lệ trong ma trận.")
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise GenerationError("Ma trận không có tỷ lệ phân bổ khả dụng.")
    exact = {key: total * value / weight_sum for key, value in weights.items()}
    counts = {key: math.floor(value) for key, value in exact.items()}
    remainder = total - sum(counts.values())
    order = {key: index for index, key in enumerate(weights)}
    for key in sorted(weights, key=lambda item: (-(exact[item] - counts[item]), order[item]))[:remainder]:
        counts[key] += 1
    return counts


def _grade_weights(rules: dict[str, Any]) -> dict[str, float]:
    ranges = rules.get("grade_weight_percent", {})
    weights = {}
    for grade, interval in ranges.items():
        if not isinstance(interval, list) or len(interval) != 2:
            raise GenerationError("Khoảng tỷ lệ lớp trong ma trận không hợp lệ.")
        low, high = (float(value) for value in interval)
        if low < 0 or high < low:
            raise GenerationError("Khoảng tỷ lệ lớp trong ma trận không hợp lệ.")
        weights[str(grade)] = (low + high) / 2
    combined = rules.get("combined_grade_weight_percent", {})
    if "10_and_11" in combined:
        low, high = (float(value) for value in combined["10_and_11"])
        if low < 0 or high < low:
            raise GenerationError("Khoảng tỷ lệ lớp gộp trong ma trận không hợp lệ.")
        weights["10_and_11"] = (low + high) / 2
    if not weights or abs(sum(weights.values()) - 100) > 0.01:
        raise GenerationError("Tỷ lệ lớp trong ma trận phải xác định đầy đủ và tổng bằng 100%.")
    return weights


def _grade_counts(total: int, rules: dict[str, Any]) -> dict[str, int]:
    category_counts = largest_remainder(total, _grade_weights(rules))
    result: dict[str, int] = {}
    for grade, amount in category_counts.items():
        if grade == "10_and_11":
            result.update(largest_remainder(amount, {"10": 1, "11": 1}))
        else:
            result[grade] = amount
    return result


def _unit_plan(rules: dict[str, Any], difficulty: dict[str, int], topics: list[Topic]) -> list[dict[str, Any]]:
    count = int(rules["prompt_count"])
    grade_counts = _grade_counts(count, rules)
    cognitive_counts = largest_remainder(count, rules["cognitive_weight_percent"])
    difficulty_counts = largest_remainder(count, difficulty)
    ordered: list[dict[str, Any]] = []
    for key, counts in (("grade", grade_counts), ("cognitive_level", cognitive_counts), ("difficulty", difficulty_counts)):
        values = [value for value, amount in counts.items() for _ in range(amount)]
        if len(values) != count:
            raise GenerationError(f"Phân bổ {key} không đủ số lệnh hỏi.")
        for index, value in enumerate(values):
            if len(ordered) <= index:
                ordered.append({})
            ordered[index][key] = int(value) if key == "grade" else value
    by_grade: dict[int, list[Topic]] = {}
    for topic in topics:
        by_grade.setdefault(topic.grade, []).append(topic)
    counters: dict[int, int] = {}
    for unit in ordered:
        grade = unit["grade"]
        grade_topics = sorted(by_grade.get(grade, []), key=lambda item: (item.code, item.id))
        if not grade_topics:
            raise GenerationError(f"Không có chủ đề lớp {grade} cho môn này.")
        idx = counters.get(grade, 0)
        topic = grade_topics[idx % len(grade_topics)]
        counters[grade] = idx + 1
        unit["topic_id"] = topic.id
        unit["topic"] = topic.name
    return ordered


def build_allocations(rules: dict[str, Any], difficulty: dict[str, int], topics: list[Topic]) -> dict[str, Any]:
    if set(difficulty) != {"easy", "medium", "hard"} or sum(difficulty.values()) != 100:
        raise GenerationError("Tỷ lệ dễ/vừa/khó phải có đủ ba mức và tổng bằng 100%.")
    units = _unit_plan(rules, difficulty, topics)
    sections = []
    offset = 0
    for section in rules["sections"]:
        amount = int(section["sub_prompts"])
        sections.append({"name": section["name"], "type": section["type"], "questions": int(section["questions"]),
                         "points": float(section["points"]), "points_per_question": section.get("points_per_question"),
                         "scoring_per_correct_item_count": section.get("scoring_per_correct_item_count"),
                         "allocations": units[offset:offset + amount]})
        offset += amount
    if offset != len(units):
        raise GenerationError("Tổng số lệnh hỏi trong các phần không khớp ma trận.")
    return {"question_count": int(rules["question_count"]), "prompt_count": len(units),
            "duration_minutes": int(rules["duration_minutes"]), "max_score": 10.0, "sections": sections,
            "allocations": units}


def _section_prompt(subject: Subject, rules: dict[str, Any], section: dict[str, Any], mode: str) -> str:
    kind = section["type"]
    format_rules = {
        "multiple_choice": "Mỗi câu có stem, đúng 4 lựa chọn A-D, answer_choice là một chữ A/B/C/D; statements, answer_true_false, accepted_answers, tolerance để null.",
        "true_false": "Mỗi nhóm có stem chung, đúng 4 mệnh đề statements theo thứ tự a,b,c,d, answer_true_false là đúng 4 boolean; các trường đáp án loại khác để null.",
        "short_answer": "Mỗi câu có stem, accepted_answers là các đáp án số tương đương dạng chuỗi và tolerance là sai số không âm; các trường đáp án loại khác để null.",
    }[kind]
    topic_scope = rules.get("topics", {})
    guardrails = "\n".join(f"- {item}" for item in rules.get("guardrails", []))
    width = 4 if kind == "true_false" else 1
    slot_plan = []
    for index in range(0, len(section["allocations"]), width):
        group = section["allocations"][index:index + width]
        slot_plan.append({"group": len(slot_plan) + 1, "scored_prompts": [
            {key: unit[key] for key in ("grade", "topic", "cognitive_level", "difficulty")} for unit in group]})
    return (
        "Bạn là người biên soạn câu hỏi luyện thi THPT bằng tiếng Việt. Chỉ tạo nội dung mới; không tự nhận là đề chính thức. "
        "Trả đúng JSON theo schema, không markdown, không văn bản ngoài JSON.\n"
        f"Môn: {subject.name}. Chế độ: {mode}. Phần: {section['name']} ({kind}).\n"
        f"Tạo chính xác {section['questions']} nhóm câu. Quy tắc đầu ra: {format_rules}\n"
        f"Kế hoạch phạm vi từng nhóm theo đúng thứ tự (bám sát lớp/chủ đề/mức tư duy/độ khó): {json.dumps(slot_plan, ensure_ascii=False)}\n"
        f"Mỗi lời giải cần nêu phép lập luận/cách tính đủ để người học kiểm tra, không chỉ lặp lại đáp án.\n"
        f"Chủ đề được phép theo lớp: {json.dumps(topic_scope, ensure_ascii=False)}\n"
        f"Nguyên tắc môn học: {guardrails}\n"
        "Không được thêm câu, thiếu câu, lồng câu hỏi phụ ngoài cấu trúc, dùng kiến thức ngoài danh sách lớp, "
        "viết phương án trùng nhau, hoặc tạo dữ kiện mơ hồ. Với câu số, dùng dấu chấm thập phân trong answer."
    )


def _plain(parsed: Any) -> SectionOutput:
    try:
        if isinstance(parsed, SectionOutput):
            return parsed
        if hasattr(parsed, "model_dump"):
            parsed = parsed.model_dump()
        return SectionOutput.model_validate(parsed)
    except (ValidationError, TypeError, ValueError) as exc:
        raise GenerationError("Gemini trả cấu trúc câu hỏi không hợp lệ; section không được lưu.") from exc


async def generate_section(subject: Subject, rules: dict[str, Any], section: dict[str, Any], *, mode: str) -> dict[str, Any]:
    prompt = _section_prompt(subject, rules, section, mode)
    try:
        parsed = await generate_structured([prompt], SectionOutput, max_output_tokens=SECTION_OUTPUT_TOKENS)
    except GeminiClientError as exc:
        raise GenerationError(str(exc)) from exc
    output = _plain(parsed)
    if len(output.questions) != section["questions"]:
        raise GenerationError(f"Phần {section['name']} trả {len(output.questions)}/{section['questions']} nhóm câu; không được lưu.")
    return {"questions": [item.model_dump() for item in output.questions]}


def validate_section_output(section: dict[str, Any], raw: dict[str, Any], *, existing_fingerprints: set[str]) -> list[dict[str, Any]]:
    output = _plain(raw)
    if len(output.questions) != section["questions"]:
        raise GenerationError("Số nhóm câu không đúng với ma trận.")
    allocations = section["allocations"]
    flattened: list[dict[str, Any]] = []
    result = []
    local_fingerprints: set[str] = set()
    for index, item in enumerate(output.questions):
        kind = section["type"]
        options: dict[str, str] | None = None
        answer: Any
        if kind == "multiple_choice":
            options = item.options
            if not options or set(key.upper() for key in options) != {"A", "B", "C", "D"}:
                raise GenerationError(f"Câu {index + 1}: câu trắc nghiệm phải có đúng A, B, C, D.")
            options = {key.upper(): str(value).strip() for key, value in options.items()}
            if any(not value for value in options.values()) or len(set(v.casefold() for v in options.values())) != 4:
                raise GenerationError(f"Câu {index + 1}: phương án rỗng hoặc bị trùng.")
            if (item.answer_choice or "").upper() not in options:
                raise GenerationError(f"Câu {index + 1}: đáp án phải là A, B, C hoặc D.")
            answer = item.answer_choice.upper()
            prompt_units = 1
        elif kind == "true_false":
            if not item.statements or len(item.statements) != 4 or any(len(s.strip()) < 6 for s in item.statements):
                raise GenerationError(f"Câu {index + 1}: đúng/sai phải có đủ 4 mệnh đề a–d.")
            if item.answer_true_false is None or len(item.answer_true_false) != 4 or any(type(v) is not bool for v in item.answer_true_false):
                raise GenerationError(f"Câu {index + 1}: đáp án đúng/sai phải có đúng 4 giá trị boolean.")
            options = {letter: statement.strip() for letter, statement in zip("abcd", item.statements)}
            answer = list(item.answer_true_false)
            prompt_units = 4
        elif kind == "short_answer":
            if not item.accepted_answers:
                raise GenerationError(f"Câu {index + 1}: thiếu đáp án ngắn.")
            try:
                accepted = [Decimal(value.strip().replace(",", ".")) for value in item.accepted_answers]
                tolerance = Decimal(item.tolerance or "0")
            except (InvalidOperation, AttributeError) as exc:
                raise GenerationError(f"Câu {index + 1}: đáp án ngắn/sai số không hợp lệ.") from exc
            if any(not value.is_finite() for value in accepted) or not tolerance.is_finite() or tolerance < 0:
                raise GenerationError(f"Câu {index + 1}: đáp án ngắn/sai số phải là số hữu hạn, sai số không âm.")
            answer = {"accepted": [str(value) for value in accepted], "tolerance": str(tolerance)}
            prompt_units = 1
        else:
            raise GenerationError("Blueprint chứa loại câu chưa hỗ trợ.")
        if len(item.explanation.strip()) < 15:
            raise GenerationError(f"Câu {index + 1}: lời giải quá ngắn để rà soát.")
        fingerprint = _question_fingerprint(kind, item.stem.strip(), options, answer)
        if fingerprint in existing_fingerprints or fingerprint in local_fingerprints:
            raise GenerationError(f"Câu {index + 1} trùng với câu đã có hoặc câu khác trong đề; section bị từ chối.")
        local_fingerprints.add(fingerprint)
        if len(flattened) + prompt_units > len(allocations):
            raise GenerationError("Số lệnh hỏi vượt ma trận.")
        prompt_metadata = allocations[len(flattened):len(flattened) + prompt_units]
        flattened.extend(prompt_metadata)
        result.append({"question_type": kind, "content": item.stem.strip(), "options": options, "answer": answer,
                       "answer_status": "unknown", "explanation": item.explanation.strip(),
                       "difficulty": prompt_metadata[0]["difficulty"],
                       "cognitive_level": prompt_metadata[0]["cognitive_level"],
                       "topic_id": prompt_metadata[0]["topic_id"], "assessment_breakdown": prompt_metadata,
                       "fingerprint": fingerprint, "fingerprint_version": FINGERPRINT_VERSION})
    if len(flattened) != len(allocations):
        raise GenerationError("Số lệnh hỏi không khớp với ma trận.")
    return result


def get_active_blueprint(db: Session, subject_slug: str) -> tuple[Subject, BlueprintVersion, dict[str, Any], list[Topic]]:
    subject = db.scalar(select(Subject).where(Subject.slug == subject_slug))
    if not subject:
        raise GenerationError("Không tìm thấy môn học.")
    blueprint = db.scalar(select(Blueprint).where(Blueprint.subject_id == subject.id, Blueprint.code == "thpt-practice"))
    version = db.scalar(select(BlueprintVersion).where(BlueprintVersion.blueprint_id == blueprint.id,
                                                       BlueprintVersion.status == "active").order_by(BlueprintVersion.version.desc())) if blueprint else None
    if not version:
        raise GenerationError("Môn học chưa có ma trận đang hoạt động.")
    rules = version.rules
    allowed_topics = {int(grade): set(names) for grade, names in rules.get("topics", {}).items()}
    topics = db.scalars(select(Topic).where(Topic.subject_id == subject.id).order_by(Topic.grade, Topic.code)).all()
    active_topics = [topic for topic in topics if topic.name in allowed_topics.get(topic.grade, set())]
    return subject, version, rules, active_topics


def existing_question_fingerprints(db: Session, subject_id: int) -> set[str]:
    return set(db.scalars(select(Question.fingerprint).where(Question.subject_id == subject_id,
                                                              Question.fingerprint.is_not(None))).all())


def exam_fingerprint(questions: list[dict[str, Any]]) -> str:
    value = json.dumps([item["fingerprint"] for item in questions], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
