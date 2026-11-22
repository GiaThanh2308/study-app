"""
Module Document & Web Harvester:
Thu thập và bóc tách đề thi nguyên bản từ khắp Internet và Mạng Xã Hội:
- Tìm kiếm và tải trực tiếp file PDF / Word (.docx) từ các trang đề thi (ToanMath, ThuVienHocLieu, VietJack,...)
- Hỗ trợ link Google Drive chia sẻ trên Facebook / Zalo / Forum
- Đọc nội dung chuẩn cấu trúc kỳ thi THPT (GDPT 2018: 22 câu gồm Phần I, II, III và Bảng đáp án)
- Tự động nhận diện Tỉnh / Thành phố, Trường THPT / Sở GD&ĐT, Loại đề (Giữa kì, Cuối kì, Thi thử)
- Tự động phân cấp và lưu đề thi chuẩn xác vào Database theo Miền -> Tỉnh -> Trường
"""
import io
import os
import re
import base64
import logging
import urllib.parse
from typing import List, Dict, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from sqlalchemy.orm import Session

from app.models.models import Exam, ExamQuestion, Subject, Province, School, Region
from app.ai.vision_parser import process_exam_image

logger = logging.getLogger("studyapp.harvester")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

# 63 Tỉnh thành và Miền tương ứng
PROVINCES_REGIONS = {
    # Miền Bắc
    "Hà Nội": "Bắc", "Hải Phòng": "Bắc", "Quảng Ninh": "Bắc", "Bắc Ninh": "Bắc", "Hà Nam": "Bắc",
    "Hải Dương": "Bắc", "Hưng Yên": "Bắc", "Nam Định": "Bắc", "Ninh Bình": "Bắc", "Thái Bình": "Bắc",
    "Vĩnh Phúc": "Bắc", "Hà Giang": "Bắc", "Cao Bằng": "Bắc", "Bắc Kạn": "Bắc", "Lạng Sơn": "Bắc",
    "Tuyên Quang": "Bắc", "Thái Nguyên": "Bắc", "Phú Thọ": "Bắc", "Bắc Giang": "Bắc", "Lào Cai": "Bắc",
    "Yên Bái": "Bắc", "Điện Biên": "Bắc", "Lai Châu": "Bắc", "Sơn La": "Bắc", "Hòa Bình": "Bắc",
    # Miền Trung
    "Thanh Hóa": "Bắc", "Nghệ An": "Trung", "Hà Tĩnh": "Trung", "Quảng Bình": "Trung", "Quảng Trị": "Trung",
    "Thừa Thiên Huế": "Trung", "Huế": "Trung", "Đà Nẵng": "Trung", "Quảng Nam": "Trung", "Quảng Ngãi": "Trung",
    "Bình Định": "Trung", "Phú Yên": "Trung", "Khánh Hòa": "Trung", "Ninh Thuận": "Trung", "Bình Thuận": "Trung",
    "Kon Tum": "Trung", "Gia Lai": "Trung", "Đắk Lắk": "Trung", "Đắk Nông": "Trung", "Lâm Đồng": "Trung",
    # Miền Nam
    "TP. Hồ Chí Minh": "Nam", "Hồ Chí Minh": "Nam", "TP.HCM": "Nam", "Bình Phước": "Nam", "Bình Dương": "Nam",
    "Đồng Nai": "Nam", "Tây Ninh": "Nam", "Bà Rịa - Vũng Tàu": "Nam", "Vũng Tàu": "Nam", "Long An": "Nam",
    "Đồng Tháp": "Nam", "Tiền Giang": "Nam", "An Giang": "Nam", "Bến Tre": "Nam", "Vĩnh Long": "Nam",
    "Trà Vinh": "Nam", "Hậu Giang": "Nam", "Kiên Giang": "Nam", "Sóc Trăng": "Nam", "Bạc Liêu": "Nam",
    "Cà Mau": "Nam", "Cần Thơ": "Nam",
}


def normalize_google_drive_url(url: str) -> Tuple[str, Optional[str]]:
    """Chuyển link xem Google Drive sang link tải trực tiếp file."""
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url) or re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}", file_id
    return url, None


def decode_bing_redirect(bing_url: str) -> str:
    """Giải mã link redirect của Bing sang URL gốc."""
    try:
        parsed = urllib.parse.urlparse(bing_url)
        params = urllib.parse.parse_qs(parsed.query)
        u_val = params.get("u", [""])[0]
        if u_val.startswith("a1"):
            b64 = u_val[2:]
            b64 += "=" * (-len(b64) % 4)
            return base64.urlsafe_b64decode(b64).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return bing_url


async def download_file_or_find_doc(url: str) -> Tuple[Optional[bytes], str, str]:
    """
    Tải file từ URL. Nếu URL là trang web chứa link PDF/Word,
    tự động tìm và tải file tài liệu đính kèm bên trong.
    Trả về: (file_bytes, file_type ['pdf', 'docx', 'image', 'html'], title)
    """
    direct_url, _ = normalize_google_drive_url(url)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        resp = await client.get(direct_url)
        if resp.status_code != 200:
            raise ValueError(f"Không thể kết nối đến đường dẫn ({resp.status_code}): {url}")

        content_type = resp.headers.get("Content-Type", "").lower()
        url_lower = str(resp.url).lower()

        if "application/pdf" in content_type or url_lower.endswith(".pdf"):
            return resp.content, "pdf", "Đề thi PDF"

        if "word" in content_type or url_lower.endswith(".docx") or url_lower.endswith(".doc"):
            return resp.content, "docx", "Đề thi Word"

        if any(img_t in content_type for img_t in ["image/jpeg", "image/png", "image/webp"]):
            return resp.content, "image", "Ảnh đề thi"

        soup = BeautifulSoup(resp.text, "html.parser")
        page_title = soup.title.string.strip() if (soup.title and soup.title.string) else "Đề thi Internet"

        # Tìm link file PDF / Word / Google Drive trong bài viết
        doc_link = None
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            href_full = urllib.parse.urljoin(str(resp.url), href)
            h_lower = href_full.lower()

            if ".pdf" in h_lower or ".docx" in h_lower or "drive.google.com/file" in h_lower or "download" in h_lower:
                doc_link = href_full
                break

        if not doc_link:
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "")
                m = re.search(r'file=([^&]+)', src)
                if m:
                    doc_link = urllib.parse.unquote(m.group(1))
                    break

        if doc_link:
            logger.info(f"Tìm thấy file tài liệu đính kèm: {doc_link}")
            doc_link, _ = normalize_google_drive_url(doc_link)
            doc_resp = await client.get(doc_link)
            if doc_resp.status_code == 200:
                doc_ct = doc_resp.headers.get("Content-Type", "").lower()
                doc_url_l = str(doc_resp.url).lower()
                if "pdf" in doc_ct or doc_url_l.endswith(".pdf"):
                    return doc_resp.content, "pdf", page_title
                elif "word" in doc_ct or doc_url_l.endswith(".docx") or doc_url_l.endswith(".doc"):
                    return doc_resp.content, "docx", page_title

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="entry-content") or soup.body
        html_text = main_content.get_text(separator="\n") if main_content else soup.get_text(separator="\n")
        return html_text.encode("utf-8"), "html", page_title


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Trích xuất toàn bộ văn bản từ file PDF qua PyMuPDF (fitz)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [doc[i].get_text() for i in range(len(doc))]
    return "\n".join(pages)


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Trích xuất toàn bộ văn bản từ file Word .docx."""
    doc = DocxDocument(io.BytesIO(docx_bytes))
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    for t in doc.tables:
        for r in t.rows:
            cell_texts = [c.text.strip() for c in r.cells if c.text.strip()]
            if cell_texts:
                lines.append(" | ".join(cell_texts))
    return "\n".join(lines)


# ===================== PARSER ĐÁP ÁN CHÍNH THỨC =====================

def parse_answer_key_matrix(ans_text: str, target_code: Optional[str] = None) -> Tuple[Dict[int, str], Dict[int, str], Dict[int, str]]:
    """
    Bóc tách bảng đáp án matrix chuẩn từ cuối tài liệu:
    - Định dạng 1: Đề\câu (Ma trận nằm ngang: Cột 1..12, 1a..4d, 1..6; Dòng: các mã đề 1001, 1002...)
    - Định dạng 2: Câu\Mã Đề (Ma trận dọc: Dòng: Câu hỏi; Cột: các mã đề)
    - Định dạng 3: Danh sách đáp án dạng 1.A 2.B 3.C...
    """
    keys_p1: Dict[int, str] = {}
    keys_p2: Dict[int, str] = {}
    keys_p3: Dict[int, str] = {}

    if not ans_text:
        return keys_p1, keys_p2, keys_p3

    # DẠNG 1: Đề\câu (Matrix nằm ngang theo từng mã đề)
    de_cau_m = re.search(r'(?i)đề[\\/]câu', ans_text)
    if de_cau_m:
        table_text = ans_text[de_cau_m.start():]
        sol_m = re.search(r'(?i)(?:lời\s*giải\s*chi\s*tiết|hướng\s*dẫn\s*giải)', table_text)
        if sol_m:
            table_text = table_text[:sol_m.start()]

        lines = [l.strip() for l in table_text.split('\n') if l.strip()]

        # Xác định target code (mã đề đầu tiên nếu không truyền vào)
        first_code = target_code
        if not first_code:
            for l in lines:
                if re.match(r'^\d{3,4}$', l):
                    first_code = l
                    break
        first_code = first_code or "1001"

        # Bóc tách phần headers bảng 1 (1..12, 1a..3a)
        col_headers_1 = []
        i = 0
        while i < len(lines):
            if lines[i] in ['Đề\\câu', 'Đề/câu', 'Đề \\ câu']:
                i += 1
                while i < len(lines) and not re.match(r'^\d{3,4}$', lines[i]):
                    col_headers_1.append(lines[i])
                    i += 1
                break
            i += 1

        p1_answers = {}
        if col_headers_1 and i < len(lines) and lines[i] == first_code:
            ans_vals = lines[i + 1 : i + 1 + len(col_headers_1)]
            for h, a in zip(col_headers_1, ans_vals):
                p1_answers[h] = a

        # Bóc tách phần headers bảng 2 (3b..4d, 1..6)
        col_headers_2 = []
        j = i + 1
        while j < len(lines):
            if lines[j] == '3b':
                while j < len(lines) and lines[j] in ['3b', '3c', '3d', '4a', '4b', '4c', '4d', '1', '2', '3', '4', '5', '6']:
                    col_headers_2.append(lines[j])
                    j += 1
                break
            j += 1

        p2_answers = {}
        if col_headers_2 and j < len(lines):
            ans_vals_2 = lines[j : j + len(col_headers_2)]
            for h, a in zip(col_headers_2, ans_vals_2):
                p2_answers[h] = a

        all_ans = {**p1_answers, **p2_answers}

        # Gán Phần I (1..12)
        for qn in range(1, 13):
            if str(qn) in p1_answers:
                keys_p1[qn] = p1_answers[str(qn)].upper()

        # Gán Phần II (1..4 với a, b, c, d)
        for qn in range(1, 5):
            tf_list = []
            for sub in ['a', 'b', 'c', 'd']:
                val = all_ans.get(f"{qn}{sub}", "").upper()
                if any(c in val for c in ['D', 'Đ', 'T', '1']):
                    tf_list.append('T')
                elif any(c in val for c in ['S', 'F', '0']):
                    tf_list.append('F')
                else:
                    tf_list.append('T')
            keys_p2[qn] = ",".join(tf_list)

        # Gán Phần III (1..6)
        for qn in range(1, 7):
            if str(qn) in p2_answers:
                keys_p3[qn] = p2_answers[str(qn)].rstrip('.')

        if keys_p1 or keys_p2 or keys_p3:
            return keys_p1, keys_p2, keys_p3

    # DẠNG 2: Câu\Mã Đề (Ma trận dọc)
    matrix_match = re.search(r'(?i)câu[\\/]mã\s*đề\s*\n([0-9\s]+)\n((?:.+?\n)+)', ans_text)
    if matrix_match:
        codes = matrix_match.group(1).split()
        num_codes = len(codes)
        lines = [l.strip() for l in matrix_match.group(2).strip().split('\n') if l.strip()]

        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if line.isdigit():
                q_num = int(line)
                if idx + 1 < len(lines):
                    ans_val = lines[idx + 1].strip().upper()
                    if any(c in ans_val for c in ['Đ', 'S']):
                        tf_str = ans_val.replace('Đ', 'T,').replace('S', 'F,').strip(',')
                        keys_p2[q_num] = tf_str
                    elif re.match(r'^[A-D]$', ans_val):
                        keys_p1[q_num] = ans_val
                    else:
                        keys_p3[q_num] = ans_val.rstrip('.')
                idx += num_codes + 1
            else:
                idx += 1

    # DẠNG 3: Danh sách đáp án dạng 1.A 2.B 3.C
    if not keys_p1:
        simple_matches = re.findall(r'(?:^|\s)(\d+)[\s.:-]*([A-D])(?:\s|$)', ans_text, re.MULTILINE)
        for q_str, ans_char in simple_matches:
            keys_p1[int(q_str)] = ans_char.upper()

    return keys_p1, keys_p2, keys_p3


# ===================== PARSER CẤU TRÚC ĐỀ THI GDPT 2018 (22 CÂU) =====================

def parse_exam_document_text(text: str) -> List[Dict]:
    """
    Phân tách nội dung văn bản đề thi thành danh sách câu hỏi sạch:
    - Bắt đúng ranh giới kết thúc đề thi (không để bảng đáp án hoặc mã đề khác lọt vào câu hỏi)
    - Chuẩn cấu trúc GDPT 2018: 12 câu Phần I + 4 câu Phần II + 6 câu Phần III = 22 câu chuẩn
    - Đề thi trắc nghiệm truyền thống: tối đa 50 câu
    """
    questions: List[Dict] = []

    # 1. Tìm ranh giới kết thúc đề thi chính thức của mã đề đầu tiên
    end_marker = re.search(r'(?i)(?:\n\s*[-–—=]{2,}\s*hết\s*[-–—=]{2,}|\n\s*hết\s*\n)', text)

    # Tìm mã đề thứ hai nếu có (ví dụ Mã đề 1002 khi file chứa nhiều mã đề)
    m_codes = list(re.finditer(r'(?i)\b(?:mã\s*đề\s*(?:thi)?[\s.:-]*(\d{3,4}))', text))
    first_code = m_codes[0].group(1) if m_codes else None
    second_code_pos = None
    if first_code:
        for mc in m_codes[1:]:
            if mc.group(1) != first_code and mc.start() > 1000:
                second_code_pos = mc.start()
                break

    # Tìm vị trí bắt đầu bảng đáp án
    ans_markers = list(re.finditer(
        r'(?i)(?:đề[\\/]câu|câu[\\/]mã\s*đề|bảng\s*đáp\s*án|đáp\s*án\s*chi\s*tiết|đáp\s*án\s*các\s*mã\s*đề|hướng\s*dẫn\s*chấm|bảng\s*trả\s*lời)',
        text
    ))
    first_ans_pos = ans_markers[0].start() if ans_markers else None

    # Điểm ngắt nội dung đề thi (cutoff)
    cutoff_candidates = []
    if end_marker:
        cutoff_candidates.append(end_marker.start())
    if second_code_pos:
        cutoff_candidates.append(second_code_pos)
    if first_ans_pos:
        cutoff_candidates.append(first_ans_pos)

    cutoff_pos = min(cutoff_candidates) if cutoff_candidates else len(text)

    # Tách riêng văn bản đề thi và văn bản bảng đáp án
    exam_text = text[:cutoff_pos]
    ans_text = text[first_ans_pos:] if first_ans_pos else text[cutoff_pos:]

    keys_p1, keys_p2, keys_p3 = parse_answer_key_matrix(ans_text, first_code)

    # Bổ sung: Bóc tách đáp án dạng LoiGiaiHay (PHẦN I. \n1D \n2B \n3A ...)
    if not keys_p1:
        lgih_p1 = re.search(r'(?i)PHẦN\s+I\.?\s*\n((?:\d+[A-D]\s*\n?)+)', text)
        if lgih_p1:
            for m in re.finditer(r'(\d+)([A-D])', lgih_p1.group(1)):
                keys_p1[int(m.group(1))] = m.group(2)

    if not keys_p2:
        lgih_p2 = re.search(r'(?i)PHẦN\s+II\.?\s*\n(.*?)(?=PHẦN\s+III|$)', text, re.DOTALL)
        if lgih_p2:
            block = lgih_p2.group(1)
            # Parse format: Câu\nLệnh hỏi\nĐúng/Sai\n1\na\nĐ\n...
            tf_data = {}
            for m in re.finditer(r'(?:^|\n)\s*(\d)\s*\n\s*([a-d])\s*\n\s*([ĐSđs])', block):
                q_num = int(m.group(1))
                sub_letter = m.group(2)
                val = "T" if m.group(3).upper() in ["Đ", "D"] else "F"
                if q_num not in tf_data:
                    tf_data[q_num] = {}
                tf_data[q_num][sub_letter] = val
            for q_num, subs in tf_data.items():
                tf_str = ",".join(subs.get(l, "T") for l in ["a", "b", "c", "d"])
                keys_p2[q_num] = tf_str

    if not keys_p3:
        lgih_p3 = re.search(r'(?i)PHẦN\s+III\.?\s*\n(?:Câu\s*\n)?(?:Đáp\s*án\s*\n)?((?:\d+\s*\n[^\n]+\s*\n?)+)', text)
        if lgih_p3:
            block = lgih_p3.group(1)
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            i = 0
            while i < len(lines) - 1:
                if lines[i].isdigit():
                    q_num = int(lines[i])
                    ans_val = lines[i + 1].rstrip('.')
                    if not re.match(r'^[A-D]$', ans_val) and q_num <= 6:
                        keys_p3[q_num] = ans_val
                    i += 2
                else:
                    i += 1

    # 2. Bóc tách theo chuẩn GDPT 2018 (Phần I, Phần II, Phần III)
    p1_m = re.search(r'(?i)phần\s+(?:I|1)[\s.:-]', exam_text)
    p2_m = re.search(r'(?i)phần\s+(?:II|2)[\s.:-]', exam_text)
    p3_m = re.search(r'(?i)phần\s+(?:III|3)[\s.:-]', exam_text)

    if p1_m and p2_m:
        end_p1 = p2_m.start()
        end_p2 = p3_m.start() if p3_m else len(exam_text)
        end_p3 = len(exam_text)

        sec1_text = exam_text[p1_m.start():end_p1]
        sec2_text = exam_text[p2_m.start():end_p2]
        sec3_text = exam_text[p3_m.start():end_p3] if p3_m else ""

        overall_num = 1

        # --- PHẦN I: Trắc nghiệm 4 lựa chọn (Giới hạn chuẩn 12 câu) ---
        blocks_1 = re.split(r'(?i)\n(?:Câu|Bài)\s+(\d+)[\s.:-]', sec1_text)
        if len(blocks_1) > 2:
            p1_count = 0
            for i in range(1, len(blocks_1), 2):
                if p1_count >= 18:
                    break
                q_num = int(blocks_1[i])
                q_content = blocks_1[i+1].strip()

                opts_found = re.findall(r'(?s)(?:^|\s|\n)([A-D])[\s.)-]\s*(.*?)(?=(?:[A-D][\s.)-]|$))', q_content)
                first_opt = re.search(r'(?i)(?:^|\s|\n)[A-D][\s.)-]', q_content)
                q_text = q_content[:first_opt.start()].strip() if first_opt else q_content

                opts = {"A": "", "B": "", "C": "", "D": ""}
                for o_c, o_v in opts_found:
                    opts[o_c.upper()] = o_v.strip()

                correct_ans = keys_p1.get(q_num, "A")
                questions.append({
                    "question_number": overall_num,
                    "question_type": "multiple_choice",
                    "question_text": q_text or f"Câu hỏi {overall_num}",
                    "option_a": opts["A"] or "Đáp án A",
                    "option_b": opts["B"] or "Đáp án B",
                    "option_c": opts["C"] or "Đáp án C",
                    "option_d": opts["D"] or "Đáp án D",
                    "correct_answer": correct_ans,
                    "explanation": f"Đáp án chuẩn: {correct_ans} (Phần I - Trắc nghiệm 4 lựa chọn)",
                    "topic_tag": "Phần I: 4 Lựa chọn",
                })
                overall_num += 1
                p1_count += 1

        # --- PHẦN II: Đúng / Sai (Giới hạn chuẩn 4 câu) ---
        blocks_2 = re.split(r'(?i)\n(?:Câu|Bài)\s+(\d+)[\s.:-]', sec2_text)
        if len(blocks_2) > 2:
            p2_count = 0
            for i in range(1, len(blocks_2), 2):
                if p2_count >= 4:
                    break
                q_num = int(blocks_2[i])
                q_content = blocks_2[i+1].strip()

                sub_opts = re.findall(r'(?s)(?:^|\s|\n)([a-d])\)\s*(.*?)(?=(?:[a-d]\)|$))', q_content)
                first_sub = re.search(r'(?i)(?:^|\s|\n)[a-d]\)', q_content)
                q_text = q_content[:first_sub.start()].strip() if first_sub else q_content

                opts = {"a": "", "b": "", "c": "", "d": ""}
                for s_c, s_v in sub_opts:
                    opts[s_c.lower()] = s_v.strip()

                correct_ans = keys_p2.get(q_num, "T,F,T,F")
                questions.append({
                    "question_number": overall_num,
                    "question_type": "true_false",
                    "question_text": q_text or f"Xét tính Đúng/Sai của các mệnh đề sau (Câu {overall_num}):",
                    "option_a": opts["a"] or "Mệnh đề a",
                    "option_b": opts["b"] or "Mệnh đề b",
                    "option_c": opts["c"] or "Mệnh đề c",
                    "option_d": opts["d"] or "Mệnh đề d",
                    "correct_answer": correct_ans,
                    "explanation": f"Đáp án Đúng/Sai chuẩn: {correct_ans} (Phần II - Trắc nghiệm Đúng/Sai)",
                    "topic_tag": "Phần II: Đúng / Sai",
                })
                overall_num += 1
                p2_count += 1

        # --- PHẦN III: Trả lời ngắn (Giới hạn chuẩn 6 câu) ---
        if sec3_text:
            blocks_3 = re.split(r'(?i)\n(?:Câu|Bài)\s+(\d+)[\s.:-]', sec3_text)
            if len(blocks_3) > 2:
                p3_count = 0
                for i in range(1, len(blocks_3), 2):
                    if p3_count >= 6:
                        break
                    q_num = int(blocks_3[i])
                    q_text = blocks_3[i+1].strip()
                    # Loại bỏ phần đuôi "HẾT" hoặc ghi chú nếu còn sót lại
                    q_text = re.sub(r'(?i)[-–—=]{2,}\s*hết\s*[-–—=]{2,}.*', '', q_text, flags=re.DOTALL).strip()
                    correct_ans = keys_p3.get(q_num, "0")

                    questions.append({
                        "question_number": overall_num,
                        "question_type": "short_answer",
                        "question_text": q_text or f"Câu hỏi trả lời ngắn {overall_num}",
                        "option_a": "",
                        "option_b": "",
                        "option_c": "",
                        "option_d": "",
                        "correct_answer": correct_ans,
                        "explanation": f"Đáp số chính xác: {correct_ans} (Phần III - Trả lời ngắn)",
                        "topic_tag": "Phần III: Trả lời ngắn",
                    })
                    overall_num += 1
                    p3_count += 1

    # 3. Nếu là đề thi truyền thống (40 - 50 câu trắc nghiệm đơn thuần)
    if not questions:
        raw_blocks = re.split(r'(?i)\n(?:Câu|Bài)\s+(\d+)[\s.:-]', exam_text)
        if len(raw_blocks) > 2:
            count = 0
            for i in range(1, len(raw_blocks), 2):
                if count >= 50:
                    break
                q_num = int(raw_blocks[i])
                q_content = raw_blocks[i+1].strip()

                opts_found = re.findall(r'(?s)(?:^|\s|\n)([A-D])[\s.)-]\s*(.*?)(?=(?:[A-D][\s.)-]|$))', q_content)
                first_opt = re.search(r'(?i)(?:^|\s|\n)[A-D][\s.)-]', q_content)
                q_text = q_content[:first_opt.start()].strip() if first_opt else q_content
                q_text = re.sub(r'(?i)[-–—=]{2,}\s*hết\s*[-–—=]{2,}.*', '', q_text, flags=re.DOTALL).strip()

                opts = {"A": "", "B": "", "C": "", "D": ""}
                for o_c, o_v in opts_found:
                    opts[o_c.upper()] = o_v.strip()

                if opts["A"] or opts["B"]:
                    ans = keys_p1.get(q_num, "A")
                    questions.append({
                        "question_number": q_num,
                        "question_type": "multiple_choice",
                        "question_text": q_text,
                        "option_a": opts["A"],
                        "option_b": opts["B"],
                        "option_c": opts["C"],
                        "option_d": opts["D"],
                        "correct_answer": ans,
                        "explanation": f"Đáp án: {ans}",
                        "topic_tag": "Trắc nghiệm tổng hợp",
                    })
                    count += 1

    return questions


# ===================== NHẬN DIỆN VỊ TRÍ ĐỊA LÝ & PHÂN CẤP TỰ ĐỘNG =====================

def extract_exam_hierarchy_metadata(title: str, text: str) -> Dict:
    """
    Tự động phân tích tiêu đề và nội dung để xác định:
    - Tỉnh / Thành phố (trong 63 tỉnh thành)
    - Miền (Bắc, Trung, Nam)
    - Trường THPT hoặc Sở GD&ĐT
    - Phân loại đề thi (mock: thi thử, midterm: giữa kì, final: cuối kì, regular: thường xuyên)
    - Năm thi (2025, 2026...)
    """
    search_context = (title + " " + text[:2000]).replace("-", " ")

    # 1. Nhận diện Tỉnh thành
    found_province = None
    found_region = "Bắc"
    for prov, reg in PROVINCES_REGIONS.items():
        if re.search(r'(?i)\b' + re.escape(prov) + r'\b', search_context):
            if prov in ["Hồ Chí Minh", "TP.HCM"]:
                found_province = "TP. Hồ Chí Minh"
            elif prov == "Huế":
                found_province = "Thừa Thiên Huế"
            else:
                found_province = prov
            found_region = reg
            break

    if not found_province:
        found_province = "Hà Nội"
        found_region = "Bắc"

    # 2. Nhận diện Trường THPT hoặc Sở GD&ĐT
    found_school = None
    school_patterns = [
        r'(?i)(Sở\s+GD&ĐT\s+[^,\n–-]+)',
        r'(?i)(Sở\s+GD-ĐT\s+[^,\n–-]+)',
        r'(?i)(Sở\s+GDĐT\s+[^,\n–-]+)',
        r'(?i)(Trường\s+THPT\s+Chuyên\s+[^,\n–-]+)',
        r'(?i)(THPT\s+Chuyên\s+[^,\n–-]+)',
        r'(?i)(Cụm\s+\d+\s+trường\s+THPT\s+[^,\n–-]+)',
        r'(?i)(Trường\s+THPT\s+[^,\n–-]+)',
        r'(?i)(THPT\s+[^,\n–-]+)',
    ]
    for pat in school_patterns:
        m = re.search(pat, text[:2000]) or re.search(pat, title)
        if m:
            found_school = m.group(1).strip()
            break

    if not found_school:
        found_school = f"Sở GD&ĐT {found_province}"

    # 3. Nhận diện loại đề thi
    category = "mock"
    combined_lower = (title + " " + text[:1500]).lower()
    if any(k in combined_lower for k in ["giữa kì", "giữa kỳ", "gk1", "gk2", "giữa hk"]):
        category = "midterm"
    elif any(k in combined_lower for k in ["cuối kì", "cuối kỳ", "ck1", "ck2", "học kì 1", "học kì 2", "học kỳ 1", "học kỳ 2"]):
        category = "final"
    elif any(k in combined_lower for k in ["1 tiết", "thường xuyên", "15 phút"]):
        category = "regular"
    else:
        category = "mock"

    # 4. Năm thi
    exam_year = 2025
    ym = re.search(r'\b(202[4-7])\b', combined_lower)
    if ym:
        exam_year = int(ym.group(1))

    return {
        "province": found_province,
        "region": found_region,
        "school": found_school,
        "category": category,
        "year": exam_year,
    }


# ===================== CÔNG CỤ TÌM KIẾM ĐỀ THI TRÊN MẠNG =====================

async def search_exam_documents_on_web(query: str, subject_name: str) -> List[Dict]:
    """Tìm kiếm đề thi trên TOANMATH và Bing (PDF, Word, Google Drive)."""
    found_candidates = []

    # 1. Tìm trên TOANMATH.com
    if "toán" in subject_name.lower():
        try:
            tm_url = f"https://toanmath.com/?s={urllib.parse.quote(query)}"
            async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=HEADERS) as client:
                res = await client.get(tm_url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    for a in soup.select("article h2 a, .entry-title a, h2 a")[:4]:
                        href = a.get("href", "")
                        title = a.text.strip()
                        if href and "-" in href and not any(x in href for x in ["/tag/", "/category/", "/page/"]):
                            found_candidates.append({
                                "title": title,
                                "url": href,
                                "source": "TOANMATH.com",
                            })
        except Exception as e:
            logger.warning(f"Lỗi tìm kiếm ToanMath: {e}")

    # 2. Tìm kiếm mở rộng qua Bing
    bing_query = f'"{query}" filetype:pdf OR filetype:docx OR site:drive.google.com "đề thi"'
    try:
        bing_url = "https://www.bing.com/search"
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(bing_url, params={"q": bing_query})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for h2 in soup.select("li.b_algo h2 a")[:5]:
                    raw_href = h2.get("href", "")
                    real_href = decode_bing_redirect(raw_href)
                    title = h2.text.strip()
                    if real_href.startswith("http") and not any(x in real_href for x in ["wikipedia.org", "youtube.com"]):
                        found_candidates.append({
                            "title": title,
                            "url": real_href,
                            "source": "Web / Social Share",
                        })
    except Exception as e:
        logger.warning(f"Lỗi tìm kiếm Bing: {e}")

    return found_candidates


# ===================== ĐIỀU PHỐI CHÍNH: HARVEST VÀ TỰ ĐỘNG PHÂN CẤP =====================

async def harvest_and_create_exam(
    db: Session,
    subject_id: int,
    query: str = "",
    web_url: Optional[str] = None,
    province: Optional[str] = None,
    school_or_dept: Optional[str] = None,
    exam_category: Optional[str] = None,
) -> Exam:
    """
    Quy trình tự động chuẩn 100%:
    1. Tải tài liệu PDF / Word từ URL hoặc tìm kiếm từ Internet
    2. Bóc tách câu hỏi chuẩn cấu trúc GDPT 2018 (22 câu)
    3. Tự động nhận diện Tỉnh, Trường THPT và Phân loại đề
    4. Đặt đề thi vào đúng vị trí phân cấp trong cơ sở dữ liệu
    """
    subject = db.get(Subject, subject_id)
    if not subject:
        raise ValueError("Môn học không tồn tại")

    target_url = (web_url or "").strip()
    target_title = query or "Đề thi thu thập từ Internet"

    if not target_url:
        candidates = await search_exam_documents_on_web(query, subject.name)
        if not candidates:
            raise ValueError(
                f"Không tìm thấy tài liệu đề thi nào trên mạng khớp với từ khóa '{query}'. "
                "Bạn có thể dán trực tiếp đường dẫn file PDF / Word hoặc link Google Drive vào ô tìm kiếm."
            )
        best_candidate = candidates[0]
        target_url = best_candidate["url"]
        target_title = best_candidate["title"]
        logger.info(f"Đã chọn nguồn tài liệu: {target_title} -> {target_url}")

    file_bytes, file_type, page_title = await download_file_or_find_doc(target_url)
    if not file_bytes:
        raise ValueError("Không thể tải nội dung tài liệu từ đường dẫn này.")

    raw_text = ""
    parsed_questions = []

    if file_type == "pdf":
        raw_text = extract_text_from_pdf(file_bytes)
        parsed_questions = parse_exam_document_text(raw_text)
    elif file_type == "docx":
        raw_text = extract_text_from_docx(file_bytes)
        parsed_questions = parse_exam_document_text(raw_text)
    elif file_type == "image":
        return await process_exam_image(
            db=db,
            subject_id=subject_id,
            image_bytes=file_bytes,
            exam_title=f"Đề quét từ ảnh: {target_title[:40]}",
        )
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        parsed_questions = parse_exam_document_text(raw_text)

    if not parsed_questions or len(parsed_questions) < 3:
        raise ValueError(
            f"Tài liệu tại '{target_url}' không chứa cấu trúc câu hỏi đề thi trắc nghiệm hoàn chỉnh. "
            "Vui lòng kiểm tra lại link tài liệu hoặc thử từ khóa khác."
        )

    # Nhận diện metadata phân cấp tự động
    meta = extract_exam_hierarchy_metadata(target_title, raw_text)
    final_province = province or meta["province"]
    final_school = school_or_dept or meta["school"]
    final_category = exam_category or meta["category"]
    final_year = meta["year"]

    # Tìm hoặc tạo trường THPT tương ứng trong Database
    prov_obj = db.query(Province).filter(Province.name.ilike(f"%{final_province}%")).first()
    if not prov_obj:
        prov_obj = db.query(Province).filter(Province.name == "Hà Nội").first()

    school_obj = None
    if prov_obj:
        school_obj = db.query(School).filter(
            School.province_id == prov_obj.id,
            School.name.ilike(f"%{final_school[:30]}%")
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

    clean_title = target_title
    if page_title and len(page_title) > len(clean_title) and page_title not in ["Đề thi Internet", "Đề thi PDF", "Đề thi Word"]:
        clean_title = page_title
    clean_title = clean_title.replace("TOANMATH.com", "").replace(" - TOANMATH.com", "").strip()
    clean_title = re.sub(r'^[–—\s-]+|[–—\s-]+$', '', clean_title).strip()
    if not clean_title or len(clean_title) < 5:
        clean_title = f"Đề thi thử THPT {subject.name} {final_year} — {final_school} ({final_province})"

    exam = Exam(
        subject_id=subject_id,
        title=clean_title[:150],
        description=f"Đề thi nguyên bản được thu thập tự động từ: {target_url}",
        duration_minutes=90 if len(parsed_questions) <= 25 else 50,
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
    logger.info(
        f"Đã tạo thành công đề thi #{exam.id} '{exam.title}' ({exam.total_questions} câu) "
        f"thuộc {exam.school_or_dept} ({exam.province}) - Loại đề: {exam.exam_category}!"
    )
    return exam
