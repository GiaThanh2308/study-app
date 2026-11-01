"""
Dynamic Continuous Web Crawler - Động Cơ Cào Đề Thi Liên Tục:
Mỗi lần người dùng bấm nút "1-Click Quét", hệ thống sẽ:
1. Đọc trạng thái crawler (trang nào đã quét, index nào đã xử lý)
2. Truy cập TRANG TIẾP THEO trên internet (ToanMath page/N, LoiGiaiHay...)
3. Thu thập danh sách link đề thi ứng viên
4. Lọc bỏ các link đã có trong DB (chống trùng lặp)
5. Tải, bóc tách và nạp 5-10 đề thi MỚI TINH vào hệ thống
6. Cập nhật trạng thái crawler (để lần bấm sau quét trang khác)
"""
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.models import Exam, ExamQuestion, Subject, Province, School, Region, CrawlerState
from app.ai.document_harvester import (
    download_file_or_find_doc,
    extract_text_from_pdf,
    extract_text_from_docx,
    parse_exam_document_text,
    extract_exam_hierarchy_metadata,
    HEADERS,
)

logger = logging.getLogger("studyapp.batch_harvester")

# ==================== CẤU HÌNH NGUỒN CÀO ĐỘNG ====================

DYNAMIC_SOURCES = {
    "toanmath_mock": {
        "subject_name": "Toán",
        "base_url": "https://toanmath.com/de-thi-thu-thpt-mon-toan",
        "page_pattern": "https://toanmath.com/de-thi-thu-thpt-mon-toan/page/{page}",
        "type": "pagination",  # Phân trang: page/1, page/2, page/3...
        "category": "mock",
        "max_pages": 20,
    },
    "toanmath_midterm": {
        "subject_name": "Toán",
        "base_url": "https://toanmath.com/de-thi-giua-hoc-ki-1-toan-12",
        "page_pattern": "https://toanmath.com/de-thi-giua-hoc-ki-1-toan-12/page/{page}",
        "type": "pagination",
        "category": "midterm",
        "max_pages": 10,
    },
    "toanmath_final": {
        "subject_name": "Toán",
        "base_url": "https://toanmath.com/de-thi-hoc-ki-1-toan-12",
        "page_pattern": "https://toanmath.com/de-thi-hoc-ki-1-toan-12/page/{page}",
        "type": "pagination",
        "category": "final",
        "max_pages": 10,
    },
    "loigiaihay_physics": {
        "subject_name": "Vật lý",
        "base_url": "https://loigiaihay.com/de-thi-thu-thpt-mon-vat-li-moi-nhat-e38676.html",
        "type": "article_list",  # Trang chứa danh sách bài viết, mỗi bài có PDF
        "category": "mock",
    },
    "loigiaihay_chemistry": {
        "subject_name": "Hóa học",
        "base_url": "https://loigiaihay.com/de-thi-thu-thpt-mon-hoa-moi-nhat-e38683.html",
        "type": "article_list",
        "category": "mock",
    },
}


# ==================== CRAWLER STATE MANAGEMENT ====================

def get_or_create_crawler_state(db: Session, source_key: str) -> CrawlerState:
    """Lấy hoặc tạo mới trạng thái crawler cho một nguồn cụ thể."""
    state = db.query(CrawlerState).filter(CrawlerState.source_key == source_key).first()
    if not state:
        state = CrawlerState(source_key=source_key, current_page=1, current_index=0, total_imported=0)
        db.add(state)
        db.flush()
    return state


def advance_crawler_state(db: Session, state: CrawlerState, new_imports: int = 0):
    """Cập nhật trạng thái crawler sau khi quét xong."""
    state.current_page += 1
    state.total_imported += new_imports
    state.last_crawled_at = datetime.now(timezone.utc)
    db.flush()


# ==================== LINK DISCOVERY (TÌM LINK MỚI TRÊN INTERNET) ====================

async def discover_toanmath_links(source_config: dict, page: int) -> List[Dict]:
    """
    Quét 1 trang ToanMath và trả về danh sách link đề thi ứng viên.
    Mỗi trang chứa ~20 link bài viết, mỗi bài viết chứa file PDF/Word đề thi.
    """
    if page == 1:
        url = source_config["base_url"]
    else:
        url = source_config["page_pattern"].format(page=page)

    candidates = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"ToanMath trang {page} trả về status {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            seen = set()
            for a in soup.find_all("a"):
                href = a.get("href", "")
                title = a.get_text(strip=True)
                # Chỉ lấy link bài viết có năm (/2025/ hoặc /2026/) và tiêu đề đủ dài
                if href and ("/202" in href) and len(title) > 25 and href not in seen:
                    # Bỏ qua link HSG, link lớp 10, lớp 11
                    if any(skip in title.lower() for skip in ["hsg", "học sinh giỏi", "lớp 10", "lớp 11", "toán 10", "toán 11"]):
                        continue
                    seen.add(href)
                    candidates.append({
                        "title": title.strip(),
                        "url": href,
                        "subject_name": source_config["subject_name"],
                        "category": source_config["category"],
                    })

    except Exception as e:
        logger.error(f"Lỗi khi quét ToanMath trang {page}: {e}")

    return candidates


async def discover_loigiaihay_links(source_config: dict, current_index: int) -> List[Dict]:
    """
    Quét trang LoiGiaiHay và trả về danh sách link bài viết chứa đề thi PDF.
    Mỗi bài viết (pattern: -a{ID}.html) chứa link tải file PDF trực tiếp.
    """
    candidates = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=HEADERS) as client:
            resp = await client.get(source_config["base_url"])
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            seen = set()
            all_articles = []
            for a in soup.find_all("a"):
                href = a.get("href", "")
                title = a.get_text(strip=True)
                # Chỉ lấy bài viết article (pattern -a{ID}.html) có tiêu đề chứa năm hoặc tên tỉnh
                if re.search(r"-a\d+\.html", href) and len(title) > 20:
                    if not href.startswith("http"):
                        href = "https://loigiaihay.com" + href
                    if href not in seen:
                        seen.add(href)
                        # Làm sạch tiêu đề: bỏ phần "Xem chi tiết" hoặc nội dung câu hỏi
                        clean_title = re.split(r"Xem\s+(?:chi\s+tiết|lời\s+giải)", title)[0].strip()
                        if len(clean_title) > 100:
                            clean_title = clean_title[:100]
                        all_articles.append({
                            "title": clean_title,
                            "url": href,
                            "subject_name": source_config["subject_name"],
                            "category": source_config["category"],
                        })

            # Trả về các bài viết từ current_index trở đi (để mỗi lần bấm lấy batch mới)
            candidates = all_articles[current_index:]

    except Exception as e:
        logger.error(f"Lỗi khi quét LoiGiaiHay: {e}")

    return candidates


# ==================== DEDUPLICATION (CHỐNG TRÙNG LẶP) ====================

def get_existing_urls(db: Session) -> set:
    """Lấy tập hợp tất cả URL nguồn gốc đã có trong DB để lọc trùng nhanh."""
    results = db.query(Exam.source_origin).filter(Exam.source_origin.isnot(None)).all()
    return {r[0].strip() for r in results if r[0]}


def is_exam_duplicate(db: Session, subject_id: int, title: str, source_url: Optional[str] = None) -> Tuple[bool, Optional[Exam]]:
    """
    Kiểm tra xem đề thi đã tồn tại trong cơ sở dữ liệu chưa:
    1. Kiểm tra theo link nguồn gốc (source_origin)
    2. Kiểm tra theo tên đề thi chuẩn hóa kết hợp môn học
    """
    if source_url:
        clean_url = source_url.strip()
        existing = db.query(Exam).filter(Exam.source_origin == clean_url).first()
        if existing:
            return True, existing

    clean_title_norm = re.sub(r'[\s\-_–—]+', ' ', title.lower()).strip()
    existing_exams = db.query(Exam).filter(Exam.subject_id == subject_id).all()
    for ex in existing_exams:
        ex_norm = re.sub(r'[\s\-_–—]+', ' ', ex.title.lower()).strip()
        if clean_title_norm == ex_norm or (len(clean_title_norm) > 20 and (clean_title_norm in ex_norm or ex_norm in clean_title_norm)):
            return True, ex

    return False, None


# ==================== IMPORT SINGLE EXAM ====================

async def sync_single_exam_entry(db: Session, item: Dict, subject_map: Dict[str, Subject]) -> Dict:
    """
    Thu thập, bóc tách và phân cấp 1 đề thi cụ thể kèm kiểm tra chống trùng lặp.
    """
    sub_name = item["subject_name"]
    subject = subject_map.get(sub_name)
    if not subject:
        return {"title": item["title"], "subject": sub_name, "status": "failed", "reason": "Không tìm thấy môn học"}

    target_url = item["url"]
    target_title = item["title"]

    # BƯỚC 1: KIỂM TRA CHỐNG TRÙNG LẶP
    is_dup, existing_exam = is_exam_duplicate(db, subject.id, target_title, target_url)
    if is_dup:
        return {
            "exam_id": existing_exam.id,
            "title": existing_exam.title,
            "subject": sub_name,
            "province": existing_exam.province or "N/A",
            "school": existing_exam.school_or_dept or "N/A",
            "category": existing_exam.exam_category or item.get("category", "mock"),
            "total_questions": existing_exam.total_questions,
            "status": "skipped_duplicate",
            "reason": f"Đã có sẵn trong hệ thống (Đề #{existing_exam.id})",
        }

    # BƯỚC 2: TẢI VÀ BÓC TÁCH NỘI DUNG TÀI LIỆU
    try:
        file_bytes, file_type, page_title = await download_file_or_find_doc(target_url)
        if not file_bytes:
            return {"title": target_title, "subject": sub_name, "status": "failed", "reason": "Không thể tải tài liệu từ link"}

        raw_text = ""
        if file_type == "pdf":
            raw_text = extract_text_from_pdf(file_bytes)
        elif file_type == "docx":
            raw_text = extract_text_from_docx(file_bytes)
        else:
            raw_text = file_bytes.decode("utf-8", errors="ignore")

        parsed_questions = parse_exam_document_text(raw_text)
        if not parsed_questions or len(parsed_questions) < 3:
            return {"title": target_title, "subject": sub_name, "status": "failed", "reason": f"Cấu trúc file không nhận diện được câu hỏi (chỉ có {len(parsed_questions) if parsed_questions else 0} câu)"}

        # BƯỚC 3: NHẬN DIỆN VỊ TRÍ ĐỊA LÝ & PHÂN CẤP TỰ ĐỘNG
        meta = extract_exam_hierarchy_metadata(page_title or target_title, raw_text)
        final_province = meta["province"]
        final_school = meta["school"]
        final_category = item.get("category") or meta["category"]
        final_year = meta["year"]

        # Tìm hoặc tạo trường THPT
        prov_obj = db.query(Province).filter(Province.name.ilike(f"%{final_province}%")).first()
        if not prov_obj:
            prov_obj = db.query(Province).filter(Province.name == "Hà Nội").first()

        school_obj = None
        if prov_obj:
            school_search = final_school[:30] if len(final_school) > 30 else final_school
            school_obj = db.query(School).filter(
                School.province_id == prov_obj.id,
                School.name.ilike(f"%{school_search}%")
            ).first()
            if not school_obj:
                s_type = "dept" if any(w in final_school.lower() for w in ["sở", "phòng"]) else "thpt"
                school_obj = School(
                    province_id=prov_obj.id,
                    name=final_school[:100],
                    school_type=s_type,
                )
                db.add(school_obj)
                db.flush()

        # Xác định thời lượng theo môn
        duration = 90 if sub_name == "Toán" else 50

        exam = Exam(
            subject_id=subject.id,
            title=(page_title or target_title)[:150],
            description=f"Đề thi nguyên bản được thu thập tự động từ: {target_url}",
            duration_minutes=duration,
            exam_type="practice",
            school_id=school_obj.id if school_obj else None,
            exam_category=final_category,
            semester="HK1",
            province=final_province,
            school_or_dept=final_school,
            exam_year=final_year,
            exam_round="Chính thức",
            curriculum_standard="GDPT 2018",
            is_authentic=True,
            source_origin=target_url,
            total_questions=len(parsed_questions),
        )
        db.add(exam)
        db.flush()

        for q in parsed_questions:
            eq = ExamQuestion(
                exam_id=exam.id,
                question_number=q["question_number"],
                question_type=q.get("question_type", "multiple_choice"),
                question_text=q["question_text"],
                option_a=q.get("option_a") or "",
                option_b=q.get("option_b") or "",
                option_c=q.get("option_c") or "",
                option_d=q.get("option_d") or "",
                correct_answer=q.get("correct_answer") or "A",
                explanation=q.get("explanation"),
                topic_tag=q.get("topic_tag"),
            )
            db.add(eq)

        db.commit()
        db.refresh(exam)
        logger.info(f"✅ Nạp mới đề #{exam.id}: '{exam.title}' ({exam.total_questions} câu) [{final_province}]")

        return {
            "exam_id": exam.id,
            "title": exam.title,
            "subject": sub_name,
            "province": final_province,
            "school": final_school,
            "category": final_category,
            "total_questions": exam.total_questions,
            "status": "imported",
            "reason": f"Đã bóc tách thành công {exam.total_questions} câu chuẩn GDPT 2018",
        }
    except Exception as e:
        logger.error(f"Lỗi khi xử lý đề '{target_title}': {e}")
        db.rollback()
        return {"title": target_title, "subject": sub_name, "status": "failed", "reason": str(e)[:200]}


# ==================== MAIN CRAWLER ENGINE ====================

async def run_nationwide_batch_harvest(db: Session, subject_ids: Optional[List[int]] = None, limit_per_source: int = 5) -> Dict:
    """
    Động cơ cào đề thi liên tục (Dynamic Continuous Crawler):
    - Đọc trạng thái crawler hiện tại (đã quét đến trang nào)
    - Truy cập TRANG TIẾP THEO trên internet
    - Tìm và nạp các đề thi MỚI chưa từng có trong hệ thống
    - Cập nhật trạng thái để lần bấm sau quét trang khác
    """
    all_subjects = db.query(Subject).all()
    subject_map = {s.name: s for s in all_subjects}
    active_subject_names = {s.name for s in all_subjects if not subject_ids or s.id in subject_ids}

    # Lấy tập URL đã có trong DB để lọc trùng nhanh
    existing_urls = get_existing_urls(db)

    results = []
    new_imported = 0
    skipped_duplicates = 0
    failed = 0
    total_scanned = 0
    sources_crawled = []

    for source_key, source_config in DYNAMIC_SOURCES.items():
        if source_config["subject_name"] not in active_subject_names:
            continue

        state = get_or_create_crawler_state(db, source_key)
        db.commit()  # Commit state creation

        # BƯỚC 1: THU THẬP DANH SÁCH LINK ỨNG VIÊN TỪ INTERNET
        candidates = []
        if source_config["type"] == "pagination":
            page = state.current_page
            max_pages = source_config.get("max_pages", 20)
            if page > max_pages:
                page = 1  # Quay vòng lại từ đầu
                state.current_page = 1

            logger.info(f"🌐 Quét {source_key} trang {page}...")
            candidates = await discover_toanmath_links(source_config, page)
            sources_crawled.append(f"{source_key} (trang {page})")

        elif source_config["type"] == "article_list":
            idx = state.current_index
            logger.info(f"🌐 Quét {source_key} từ index {idx}...")
            candidates = await discover_loigiaihay_links(source_config, idx)
            sources_crawled.append(f"{source_key} (index {idx})")

        if not candidates:
            logger.info(f"Nguồn {source_key} không tìm thấy link mới, bỏ qua.")
            # Vẫn tăng page để lần sau thử trang khác
            if source_config["type"] == "pagination":
                advance_crawler_state(db, state, 0)
                db.commit()
            continue

        # BƯỚC 2: LỌC BỎ LINK ĐÃ CÓ TRONG DB (CHỐNG TRÙNG LẶP NHANH)
        new_candidates = [c for c in candidates if c["url"] not in existing_urls]
        skipped_this_source = len(candidates) - len(new_candidates)
        skipped_duplicates += skipped_this_source

        if not new_candidates:
            logger.info(f"Tất cả {len(candidates)} link từ {source_key} đều đã có trong DB. Lật trang.")
            if source_config["type"] == "pagination":
                advance_crawler_state(db, state, 0)
            elif source_config["type"] == "article_list":
                state.current_index += len(candidates)
                state.last_crawled_at = datetime.now(timezone.utc)
                db.flush()
            db.commit()
            continue

        # BƯỚC 3: TẢI, BÓC TÁCH VÀ NẠP CÁC ĐỀ MỚI (giới hạn limit_per_source đề/nguồn)
        imported_this_source = 0
        for item in new_candidates[:limit_per_source]:
            total_scanned += 1
            res = await sync_single_exam_entry(db, item, subject_map)
            results.append(res)

            if res["status"] == "imported":
                new_imported += 1
                imported_this_source += 1
                existing_urls.add(item["url"])  # Cập nhật set để các item sau không trùng
            elif res["status"] == "skipped_duplicate":
                skipped_duplicates += 1
            else:
                failed += 1

        # BƯỚC 4: CẬP NHẬT TRẠNG THÁI CRAWLER
        if source_config["type"] == "pagination":
            advance_crawler_state(db, state, imported_this_source)
        elif source_config["type"] == "article_list":
            state.current_index += min(len(new_candidates), limit_per_source)
            state.total_imported += imported_this_source
            state.last_crawled_at = datetime.now(timezone.utc)
            db.flush()

        db.commit()

    summary_msg = (
        f"⚡ Đã hoàn tất quét động liên tục: "
        f"Nạp mới {new_imported} đề thi, "
        f"bỏ qua {skipped_duplicates} đề đã tồn tại, "
        f"lỗi {failed} đề. "
        f"Nguồn đã quét: {', '.join(sources_crawled)}. "
        f"Mỗi lần bấm nút sẽ tự động lật sang trang tiếp theo trên Internet để nạp thêm đề mới!"
    )

    return {
        "success": True,
        "total_scanned": total_scanned + skipped_duplicates,
        "new_imported": new_imported,
        "skipped_duplicates": skipped_duplicates,
        "failed": failed,
        "sources_crawled": sources_crawled,
        "message": summary_msg,
        "results": results,
    }
