"""
API Phân cấp kho đề thi theo 3 Miền -> Tỉnh / Thành phố -> Trường THPT -> Loại đề thi.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.models import models, schemas

logger = logging.getLogger("studyapp.hierarchy")
router = APIRouter()


@router.get("/hierarchy/regions", response_model=List[schemas.RegionOut])
def list_regions(db: Session = Depends(get_db)):
    """Lấy danh sách 3 miền (Bắc, Trung, Nam) kèm số lượng tỉnh và đề thi."""
    regions = db.query(models.Region).order_by(models.Region.id).all()
    res = []
    for r in regions:
        # Đếm số đề thi thuộc các trường của miền này
        exam_cnt = (
            db.query(models.Exam)
            .join(models.School, models.Exam.school_id == models.School.id)
            .join(models.Province, models.School.province_id == models.Province.id)
            .filter(models.Province.region_id == r.id)
            .count()
        )
        res.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "province_count": len(r.provinces),
            "exam_count": exam_cnt,
            "provinces": [],
        })
    return res


@router.get("/hierarchy/regions/{region_id}/provinces", response_model=List[schemas.ProvinceOut])
def list_provinces_by_region(
    region_id: int,
    has_exams_only: bool = False,
    db: Session = Depends(get_db)
):
    """Lấy danh sách tỉnh thành theo miền, có thể lọc các tỉnh đã có đề thi."""
    provinces = (
        db.query(models.Province)
        .filter(models.Province.region_id == region_id)
        .order_by(models.Province.name)
        .all()
    )
    res = []
    for p in provinces:
        exam_cnt = (
            db.query(models.Exam)
            .join(models.School, models.Exam.school_id == models.School.id)
            .filter(models.School.province_id == p.id)
            .count()
        )
        if has_exams_only and exam_cnt == 0:
            continue
        res.append({
            "id": p.id,
            "region_id": p.region_id,
            "name": p.name,
            "code": p.code,
            "school_count": len(p.schools),
            "exam_count": exam_cnt,
            "schools": [],
        })
    return res


@router.get("/hierarchy/provinces/{province_id}/schools", response_model=List[schemas.SchoolOut])
def list_schools_by_province(province_id: int, db: Session = Depends(get_db)):
    """Lấy danh sách trường THPT và Sở GD&ĐT trong tỉnh kèm số đề thi."""
    schools = (
        db.query(models.School)
        .filter(models.School.province_id == province_id)
        .order_by(models.School.name)
        .all()
    )
    res = []
    for s in schools:
        exam_cnt = db.query(models.Exam).filter(models.Exam.school_id == s.id).count()
        res.append({
            "id": s.id,
            "province_id": s.province_id,
            "name": s.name,
            "school_type": s.school_type or "thpt",
            "exam_count": exam_cnt,
        })
    return res


@router.get("/hierarchy/schools/{school_id}/exams")
def list_exams_by_school(
    school_id: int,
    subject_id: Optional[int] = None,
    category: Optional[str] = None,  # "mock" | "midterm" | "final" | "regular"
    db: Session = Depends(get_db)
):
    """Lấy danh sách đề thi của trường THPT, phân loại theo loại đề thi (giữa kì, cuối kì, thi thử,...)."""
    school = db.get(models.School, school_id)
    if not school:
        raise HTTPException(404, "Trường THPT không tồn tại")

    q = db.query(models.Exam).filter(models.Exam.school_id == school_id)
    if subject_id:
        q = q.filter(models.Exam.subject_id == subject_id)
    if category and category != "all":
        q = q.filter(models.Exam.exam_category == category)

    exams = q.order_by(models.Exam.created_at.desc()).all()
    
    # Gom nhóm theo loại đề
    categorized = {
        "mock": [],      # Đề thi thử THPT
        "midterm": [],   # Đề thi giữa kì
        "final": [],     # Đề thi cuối kì
        "regular": [],   # Đề kiểm tra thường xuyên / 1 tiết
    }
    
    for ex in exams:
        cat = ex.exam_category or "mock"
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append({
            "id": ex.id,
            "subject_id": ex.subject_id,
            "title": ex.title,
            "description": ex.description,
            "duration_minutes": ex.duration_minutes,
            "exam_type": ex.exam_type,
            "exam_category": ex.exam_category or "mock",
            "semester": ex.semester or "HK1",
            "total_questions": ex.total_questions,
            "province": ex.province,
            "school_or_dept": ex.school_or_dept,
            "exam_year": ex.exam_year or 2025,
            "exam_round": ex.exam_round or "Lần 1",
            "curriculum_standard": ex.curriculum_standard or "GDPT 2018",
            "is_authentic": ex.is_authentic,
            "created_at": ex.created_at,
        })

    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "school_type": school.school_type,
            "province_name": school.province.name if school.province else "",
            "region_name": school.province.region.name if (school.province and school.province.region) else "",
        },
        "total_exams": len(exams),
        "exams_by_category": categorized,
        "all_exams": [
            {
                "id": ex.id,
                "subject_id": ex.subject_id,
                "title": ex.title,
                "description": ex.description,
                "duration_minutes": ex.duration_minutes,
                "exam_type": ex.exam_type,
                "exam_category": ex.exam_category or "mock",
                "semester": ex.semester or "HK1",
                "total_questions": ex.total_questions,
                "province": ex.province,
                "school_or_dept": ex.school_or_dept,
                "exam_year": ex.exam_year or 2025,
                "curriculum_standard": ex.curriculum_standard or "GDPT 2018",
                "created_at": ex.created_at,
            }
            for ex in exams
        ]
    }


@router.get("/hierarchy/tree")
def get_hierarchy_tree(subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Trả về toàn bộ cây phân cấp Miền -> Tỉnh -> Trường kèm số lượng đề thi phục vụ thanh điều hướng."""
    regions = db.query(models.Region).order_by(models.Region.id).all()
    tree = []

    for r in regions:
        r_node = {
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "total_exams": 0,
            "provinces": [],
        }

        for p in r.provinces:
            p_node = {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "total_exams": 0,
                "schools": [],
            }

            for s in p.schools:
                eq = db.query(models.Exam).filter(models.Exam.school_id == s.id)
                if subject_id:
                    eq = eq.filter(models.Exam.subject_id == subject_id)
                s_exams = eq.all()
                if len(s_exams) > 0:
                    s_node = {
                        "id": s.id,
                        "name": s.name,
                        "school_type": s.school_type,
                        "total_exams": len(s_exams),
                        "categories": {
                            "mock": sum(1 for e in s_exams if (e.exam_category or "mock") == "mock"),
                            "midterm": sum(1 for e in s_exams if e.exam_category == "midterm"),
                            "final": sum(1 for e in s_exams if e.exam_category == "final"),
                            "regular": sum(1 for e in s_exams if e.exam_category == "regular"),
                        }
                    }
                    p_node["schools"].append(s_node)
                    p_node["total_exams"] += len(s_exams)

            r_node["total_exams"] += p_node["total_exams"]
            # Luôn thêm tỉnh nếu có trường có đề thi hoặc thêm vào danh sách
            r_node["provinces"].append(p_node)

        tree.append(r_node)

    return tree
