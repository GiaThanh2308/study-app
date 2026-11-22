"""Idempotently seed the 3 subjects, matrix topics, and generation blueprints."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.domain import Blueprint, BlueprintVersion, Subject, Topic


SEED_DIR = Path(__file__).resolve().parent
MATRIX_PATH = SEED_DIR / "matran.md"
RULES_PATH = SEED_DIR / "matran_2027.json"


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "topic"


def seed_initial_data() -> dict[str, int]:
    matrix_bytes = MATRIX_PATH.read_bytes()
    source_sha256 = hashlib.sha256(matrix_bytes).hexdigest()
    matrix = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    topic_count = 0
    blueprint_count = 0

    with SessionLocal.begin() as db:
        for subject_data in matrix["subjects"]:
            subject = db.scalar(select(Subject).where(Subject.slug == subject_data["slug"]))
            if subject is None:
                subject = Subject(
                    slug=subject_data["slug"],
                    name=subject_data["name"],
                    icon=subject_data["icon"],
                )
                db.add(subject)
                db.flush()
            else:
                subject.name = subject_data["name"]
                subject.icon = subject_data["icon"]

            for grade_text, topic_names in subject_data["topics"].items():
                grade = int(grade_text)
                for topic_name in topic_names:
                    code = f"g{grade}-{_slug(topic_name)}"[:80]
                    topic = db.scalar(
                        select(Topic).where(
                            Topic.subject_id == subject.id,
                            Topic.code == code,
                        )
                    )
                    if topic is None:
                        db.add(
                            Topic(
                                subject_id=subject.id,
                                code=code,
                                name=topic_name,
                                grade=grade,
                                reference=matrix["source_basis"],
                            )
                        )
                        topic_count += 1

            blueprint = db.scalar(
                select(Blueprint).where(
                    Blueprint.subject_id == subject.id,
                    Blueprint.code == "thpt-practice",
                )
            )
            if blueprint is None:
                blueprint = Blueprint(
                    subject_id=subject.id,
                    code="thpt-practice",
                    name="Đề luyện tốt nghiệp THPT",
                    exam_category="practice_generation",
                )
                db.add(blueprint)
                db.flush()

            latest = db.scalar(
                select(BlueprintVersion)
                .where(BlueprintVersion.blueprint_id == blueprint.id)
                .order_by(BlueprintVersion.version.desc())
                .limit(1)
            )
            if latest is None or latest.source_sha256 != source_sha256:
                if latest is not None:
                    latest.status = "superseded"
                next_version = 1 if latest is None else latest.version + 1
                rules = {
                    **subject_data,
                    "blueprint_version": next_version,
                    "source_reference": matrix["source_filename"],
                    "source_basis": matrix["source_basis"],
                    "source_sha256": source_sha256,
                }
                db.add(
                    BlueprintVersion(
                        blueprint_id=blueprint.id,
                        version=next_version,
                        status="active",
                        source_filename=matrix["source_filename"],
                        source_sha256=source_sha256,
                        rules=rules,
                    )
                )
                blueprint_count += 1

    return {"subjects": len(matrix["subjects"]), "topics_added": topic_count, "blueprints_added": blueprint_count}


if __name__ == "__main__":
    counts = seed_initial_data()
    print(
        "Seed complete: "
        f"{counts['subjects']} subjects; "
        f"{counts['topics_added']} topics added; "
        f"{counts['blueprints_added']} blueprint versions added."
    )
