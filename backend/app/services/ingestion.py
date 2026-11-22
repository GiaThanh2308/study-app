"""Immutable source storage and deterministic exam staging helpers."""

import asyncio
import hashlib
import ipaddress
import io
import json
import re
import socket
import unicodedata
import zipfile
from email.message import Message
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClientError, extract_text_from_image, is_gemini_configured
from app.core.database import DATA_DIR
from app.models.domain import (
    DuplicateCandidate,
    Exam,
    ExamQuestionLink,
    ImportJob,
    Question,
    SourceRecord,
    StagedExam,
)


MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 2_000_000
MAX_PDF_PAGES = 500
FINGERPRINT_VERSION = 1
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".jpg", ".jpeg", ".png", ".webp"}
REDIRECT_CODES = {301, 302, 303, 307, 308}
USER_AGENT = "StudyApp-local-exam-import/1.0"


class IngestionError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def normalize_text_for_fingerprint(text: str) -> str:
    """Create a derived comparison string; never write it back to source data."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _content_fingerprint(text: str) -> str | None:
    canonical = normalize_text_for_fingerprint(text)
    return _sha256(canonical.encode("utf-8")) if canonical else None


def _sanitize_filename(filename: str | None, fallback: str) -> str:
    name = Path((filename or fallback).replace("\\", "/")).name
    name = re.sub(r"[^\w.() -]+", "_", name, flags=re.UNICODE).strip(" .")
    return (name or fallback)[:240]


def _detect_format(data: bytes, filename: str | None = None, content_type: str | None = None) -> tuple[str, str]:
    ext = Path(filename or "").suffix.lower()
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if data.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                if "word/document.xml" in names:
                    members = archive.infolist()
                    total_uncompressed = sum(item.file_size for item in members)
                    unsafe_member = any(
                        item.file_size > 50 * 1024 * 1024
                        or item.file_size > max(1, item.compress_size) * 1000
                        for item in members
                    )
                    if total_uncompressed > 100 * 1024 * 1024 or unsafe_member:
                        raise IngestionError("Tệp DOCX vượt giới hạn giải nén an toàn.")
                    return ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except zipfile.BadZipFile:
            pass
    if mime in {"text/html", "application/xhtml+xml"} or re.match(rb"\s*<(?:!doctype\s+html|html|head|body)\b", data[:2048], re.I):
        return ".html", "text/html"
    if mime.startswith("image/") and ext in {".jpg", ".jpeg", ".png", ".webp"}:
        return ext, mime
    if mime == "application/pdf" and ext == ".pdf":
        raise IngestionError("Nội dung phản hồi không có chữ ký PDF hợp lệ.")
    if mime.startswith("text/") or ext in {".txt", ".md"}:
        if b"\x00" in data[:4096]:
            raise IngestionError("Tệp văn bản có nội dung nhị phân không được hỗ trợ.")
        return (ext if ext in {".txt", ".md"} else ".txt"), "text/plain"
    if ext in ALLOWED_EXTENSIONS:
        raise IngestionError("Định dạng tệp không khớp nội dung thực tế.")
    raise IngestionError("Chỉ nhận PDF, DOCX, văn bản, HTML hoặc ảnh JPG/PNG/WebP.")


async def _assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise IngestionError("URL nguồn phải bắt đầu bằng http:// hoặc https://.")
    if parsed.username or parsed.password:
        raise IngestionError("URL có thông tin đăng nhập không được hỗ trợ.")
    host = parsed.hostname.rstrip(".").casefold()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal", ".lan")):
        raise IngestionError("URL trỏ tới host nội bộ, không được tải.", 403)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise IngestionError("Chỉ cho tải URL web ở cổng chuẩn 80/443.", 403)
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise IngestionError("URL trỏ tới địa chỉ IP không công khai, không được tải.", 403)
        return
    except ValueError:
        pass
    try:
        loop = asyncio.get_running_loop()
        addresses = await asyncio.wait_for(
            loop.run_in_executor(None, socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM),
            timeout=4.0,
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise IngestionError("Không phân giải được host URL nguồn.", 422) from exc
    ips = {ipaddress.ip_address(item[4][0]) for item in addresses}
    if not ips or any(not address.is_global for address in ips):
        raise IngestionError("URL phân giải tới địa chỉ mạng nội bộ/không công khai.", 403)


def _filename_from_headers(headers, final_url: str) -> str:
    disposition = headers.get("content-disposition", "")
    message = Message()
    message["content-disposition"] = disposition
    filename = message.get_filename()
    if filename:
        filename = unquote(filename)
    else:
        filename = Path(urlparse(final_url).path).name
    return _sanitize_filename(filename, "exam-source")


async def download_public_source(url: str) -> tuple[bytes, str, str, str]:
    current_url = url.strip()
    timeout = httpx.Timeout(20.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
            for _ in range(6):
                await _assert_public_url(current_url)
                async with client.stream("GET", current_url) as response:
                    if response.status_code in REDIRECT_CODES:
                        location = response.headers.get("location")
                        if not location:
                            raise IngestionError("Nguồn trả về redirect nhưng thiếu URL đích.")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code != 200:
                        raise IngestionError(f"Nguồn trả về HTTP {response.status_code}.", 422)
                    length = response.headers.get("content-length")
                    if length and length.isdigit() and int(length) > MAX_SOURCE_BYTES:
                        raise IngestionError("Tệp nguồn vượt giới hạn 20 MB.", 413)
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_SOURCE_BYTES:
                            raise IngestionError("Tệp nguồn vượt giới hạn 20 MB.", 413)
                    final_url = str(response.url)
                    filename = _filename_from_headers(response.headers, final_url)
                    content_type = response.headers.get("content-type", "application/octet-stream")
                    return bytes(chunks), filename, content_type, final_url
    except IngestionError:
        raise
    except httpx.TimeoutException as exc:
        raise IngestionError("Tải nguồn web quá thời gian chờ.", 504) from exc
    except httpx.RequestError as exc:
        raise IngestionError("Không tải được URL nguồn. Kiểm tra kết nối hoặc thử tải file thủ công.", 502) from exc
    raise IngestionError("URL nguồn chuyển hướng quá nhiều lần.", 422)


def extract_text(data: bytes, extension: str, content_type: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        if extension == ".pdf":
            reader = PdfReader(io.BytesIO(data), strict=False)
            if len(reader.pages) > MAX_PDF_PAGES:
                raise IngestionError(f"PDF vượt giới hạn {MAX_PDF_PAGES} trang.", 413)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif extension == ".docx":
            document = DocxDocument(io.BytesIO(data))
            parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
            parts.extend(cell.text for table in document.tables for row in table.rows for cell in row.cells if cell.text)
            text = "\n".join(parts)
        elif extension in {".txt", ".md"}:
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = data.decode("cp1258", errors="strict")
        elif extension in {".html", ".htm"}:
            soup = BeautifulSoup(data, "html.parser")
            for node in soup(["script", "style", "noscript", "svg"]):
                node.decompose()
            text = soup.get_text("\n", strip=False)
        else:
            text = ""
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Không trích xuất được text từ tệp. Nguồn gốc vẫn chưa được thay đổi.") from exc

    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        text = text[:MAX_EXTRACTED_TEXT_CHARS]
        warnings.append("Phần text dẫn xuất bị giới hạn 2 triệu ký tự; file nguồn đầy đủ vẫn được giữ nguyên.")
    if not text.strip():
        warnings.append("Không trích xuất được text. Nguồn gốc đã lưu; có thể nhập nội dung thủ công ở bản preview.")
    return text, warnings


def _parse_answer_key(text: str) -> tuple[dict[int, object], str]:
    marker = re.search(r"(?im)^\s*(?:BẢNG\s+)?ĐÁP\s+ÁN(?:\s+(?:THAM\s+KHẢO|VÀ\s+LỜI\s+GIẢI))?\s*:?\s*$", text)
    if not marker:
        return {}, text
    key_text = text[marker.end():]
    answer_map: dict[int, object] = {}
    for match in re.finditer(r"(?i)(?:Câu\s*)?(\d{1,3})\s*[:.)-]?\s*([ABCD])\b", key_text):
        answer_map[int(match.group(1))] = {"choice": match.group(2).upper()}
    for line in key_text.splitlines():
        tf = re.match(
            r"(?i)^\s*(?:Câu\s*)?(\d{1,3})\s*[:.)-]\s*((?:(?:đúng|sai|đ|s|t|f)\s*[,;/\s]+){2,}(?:đúng|sai|đ|s|t|f))\s*$",
            line,
        )
        if tf:
            tokens = re.findall(r"(?i)đúng|sai|\b[đstf]\b", tf.group(2))
            if len(tokens) == 4:
                answer_map[int(tf.group(1))] = ["T" if token.casefold() in {"đúng", "đ", "t"} else "F" for token in tokens]
            continue
        short = re.match(r"(?i)^\s*(?:Câu\s*)?(\d{1,3})\s*[:.)-]\s*([-+]?\d+(?:[.,]\d+)?)\s*$", line)
        if short and int(short.group(1)) not in answer_map:
            answer_map[int(short.group(1))] = {"accepted": [short.group(2).replace(",", ".")], "tolerance": "0"}
    return answer_map, text[:marker.start()]


def parse_questions(text: str) -> list[dict]:
    answer_map, question_text = _parse_answer_key(text)
    starts = list(re.finditer(r"(?im)^\s*(?:Câu(?:\s+hỏi)?|Bài)\s*(\d{1,3})\s*[:.)-]\s*", question_text))
    if len(starts) < 2:
        starts = list(re.finditer(r"(?im)^\s*(\d{1,3})\s*[.)]\s+", question_text))
    questions: list[dict] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(question_text)
        block = question_text[start.start():end].strip()
        source_number = int(start.group(1))
        upper_matches = list(re.finditer(r"(?<![A-Za-z0-9])([ABCD])[.)]\s*", block))
        upper_labels = {match.group(1) for match in upper_matches}
        lower_matches = list(re.finditer(r"(?<![A-Za-z0-9])([a-d])[.)]\s*", block))
        lower_labels = {match.group(1).lower() for match in lower_matches}
        question_type = "unknown"
        options = None
        content = block
        if {"A", "B", "C", "D"}.issubset(upper_labels):
            question_type = "multiple_choice"
            options = {}
            for option_index, match in enumerate(upper_matches):
                option_end = upper_matches[option_index + 1].start() if option_index + 1 < len(upper_matches) else len(block)
                options[match.group(1)] = block[match.end():option_end].strip()
            content = block[:upper_matches[0].start()].strip()
        elif {"a", "b", "c", "d"}.issubset(lower_labels):
            question_type = "true_false"
            options = {}
            for option_index, match in enumerate(lower_matches):
                option_end = lower_matches[option_index + 1].start() if option_index + 1 < len(lower_matches) else len(block)
                options[match.group(1).lower()] = block[match.end():option_end].strip()
            content = block[:lower_matches[0].start()].strip()
        elif block:
            question_type = "short_answer"
        item = {
            "position": len(questions) + 1,
            "source_number": source_number,
            "question_type": question_type,
            "content": content or block,
            "options": options,
            "candidate_answer": answer_map.get(source_number),
            "answer_status": "unknown",
            "explanation": None,
            "topic_id": None,
            "points": None,
        }
        questions.append(item)
    return questions


def _question_fingerprint(question_type: str, content: str, options: object, answer: object = None) -> str:
    value = {
        "type": question_type,
        "content": normalize_text_for_fingerprint(content),
        "options": options,
        "answer": answer,
    }
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(serialized.encode("utf-8"))


def _stem_fingerprint(question_type: str, content: str, options: object) -> str:
    return _question_fingerprint(question_type, content, options)


def _store_raw_source(data: bytes, sha256: str) -> tuple[str, bool]:
    path = DATA_DIR / "sources" / sha256[:2] / sha256
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != len(data):
            raise IngestionError("Đường dẫn content-addressed bị xung đột; nguồn chưa được ghi.", 500)
        return path.relative_to(DATA_DIR).as_posix(), False
    try:
        with path.open("xb") as handle:
            handle.write(data)
    except FileExistsError:
        return path.relative_to(DATA_DIR).as_posix(), False
    return path.relative_to(DATA_DIR).as_posix(), True


async def extract_exam_source(data: bytes, extension: str, content_type: str) -> tuple[str, list[str]]:
    text, warnings = extract_text(data, extension, content_type)
    if extension not in {".jpg", ".jpeg", ".png", ".webp"} or text.strip() or not is_gemini_configured():
        if extension in {".jpg", ".jpeg", ".png", ".webp"} and not is_gemini_configured():
            warnings.append("Ảnh đã lưu nguyên bản; OCR tùy chọn cần GEMINI_API_KEY hoặc bạn có thể dán phần text.")
        return text, warnings
    mime_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[extension]
    try:
        text = await extract_text_from_image(
            "Chép lại nguyên văn chữ nhìn thấy trong ảnh, giữ thứ tự các dòng và nhãn câu/đáp án. "
            "Không giải bài, không suy luận đáp án, không sửa hoặc hoàn thiện phần mờ; ghi [không đọc rõ] nếu cần. "
            "Chỉ trả về nội dung được nhìn thấy.",
            data,
            mime_type,
        )
        warnings.append("Text từ ảnh là OCR AI dẫn xuất; hãy so với file ảnh gốc trước khi xuất bản hoặc xác minh đáp án.")
    except GeminiClientError:
        warnings.append("OCR Gemini chưa khả dụng; ảnh gốc vẫn được giữ và có thể nhập text thủ công.")
    return text, warnings


def _add_duplicate_candidate(
    db: Session,
    *,
    left_kind: str,
    left_id: int,
    right_kind: str,
    right_id: int,
    match_kind: str,
    similarity: float,
) -> bool:
    existing = db.scalar(
        select(DuplicateCandidate).where(
            DuplicateCandidate.left_kind == left_kind,
            DuplicateCandidate.left_id == left_id,
            DuplicateCandidate.right_kind == right_kind,
            DuplicateCandidate.right_id == right_id,
        )
    )
    if existing:
        return False
    db.add(
        DuplicateCandidate(
            left_kind=left_kind,
            left_id=left_id,
            right_kind=right_kind,
            right_id=right_id,
            match_kind=match_kind,
            similarity=similarity,
            status="pending",
        )
    )
    return True


def _find_duplicate_candidates(db: Session, source: SourceRecord, questions: list[dict], subject_id: int | None) -> int:
    count = 0
    same_bytes = db.scalars(
        select(SourceRecord).where(SourceRecord.sha256 == source.sha256, SourceRecord.id != source.id)
    ).all()
    for record in same_bytes:
        count += _add_duplicate_candidate(
            db, left_kind="source_record", left_id=source.id, right_kind="source_record",
            right_id=record.id, match_kind="exact_file", similarity=1.0,
        )
    if source.content_fingerprint:
        same_content = db.scalars(
            select(SourceRecord).where(
                SourceRecord.content_fingerprint == source.content_fingerprint,
                SourceRecord.id != source.id,
            )
        ).all()
        for record in same_content:
            count += _add_duplicate_candidate(
                db, left_kind="source_record", left_id=source.id, right_kind="source_record",
                right_id=record.id, match_kind="exact_content", similarity=1.0,
            )

    staged_stems = {
        _stem_fingerprint(item["question_type"], item["content"], item.get("options"))
        for item in questions
        if item.get("content")
    }
    if not subject_id or len(staged_stems) < 3:
        return count
    rows = db.execute(
        select(Exam.id, Question.question_type, Question.content, Question.options)
        .join(ExamQuestionLink, ExamQuestionLink.question_id == Question.id)
        .join(Exam, Exam.id == ExamQuestionLink.exam_id)
        .where(Exam.status == "published", Exam.subject_id == subject_id)
    ).all()
    published_stems: dict[int, set[str]] = {}
    for exam_id, question_type, content, options in rows:
        published_stems.setdefault(exam_id, set()).add(_stem_fingerprint(question_type, content, options))
    for exam_id, stems in published_stems.items():
        union = staged_stems | stems
        similarity = len(staged_stems & stems) / len(union) if union else 0.0
        if similarity >= 0.75 and len(staged_stems & stems) >= 3:
            count += _add_duplicate_candidate(
                db, left_kind="source_record", left_id=source.id, right_kind="exam",
                right_id=exam_id, match_kind="near_questions", similarity=similarity,
            )
    return count


async def stage_source(
    db: Session,
    *,
    data: bytes,
    filename: str | None,
    content_type: str,
    source_kind: str,
    source_url: str | None,
    input_reference: str,
    metadata: dict,
    raw_text_override: str | None = None,
) -> StagedExam:
    if not data:
        raise IngestionError("Nguồn đề đang trống.")
    if len(data) > MAX_SOURCE_BYTES:
        raise IngestionError("Nguồn đề vượt giới hạn 20 MB.", 413)
    safe_filename = _sanitize_filename(filename, "pasted-exam.txt")
    extension, detected_type = _detect_format(data, safe_filename, content_type)
    if extension not in ALLOWED_EXTENSIONS:
        raise IngestionError("Định dạng nguồn chưa được hỗ trợ.")
    text, warnings = await extract_exam_source(data, extension, detected_type)
    if raw_text_override is not None:
        text = raw_text_override
    questions = parse_questions(text) if text.strip() else []
    if text.strip() and not questions:
        warnings.append("Không nhận dạng chắc chắn được cấu trúc câu; nguồn được giữ để xem/đối chiếu thủ công.")
    if any(item["question_type"] == "unknown" for item in questions):
        warnings.append("Có câu chưa nhận diện được dạng; các câu này sẽ không thể chấm tự động cho tới khi duyệt lại.")

    title = (metadata.get("title") or Path(safe_filename).stem or "Đề thi nhập vào").strip()[:300]
    staged_data = {
        "metadata": {**metadata, "title": title},
        "questions": questions,
    }
    source_sha = _sha256(data)
    content_fp = _content_fingerprint(text)
    raw_path, created_file = _store_raw_source(data, source_sha)
    job = ImportJob(source_kind=source_kind, input_reference=input_reference, status="needs_review")
    db.add(job)
    db.flush()
    source = SourceRecord(
        source_kind=source_kind,
        source_url=source_url,
        original_filename=safe_filename,
        sha256=source_sha,
        content_fingerprint=content_fp,
        fingerprint_version=FINGERPRINT_VERSION if content_fp else None,
        raw_file_path=raw_path,
        raw_text=raw_text_override,
        metadata_json={"content_type": detected_type, "extension": extension, "source_url": source_url},
    )
    db.add(source)
    db.flush()
    stage = StagedExam(
        import_job_id=job.id,
        source_record_id=source.id,
        raw_payload=text or None,
        extracted_data=staged_data,
        warnings=warnings,
        status="needs_review",
    )
    db.add(stage)
    db.flush()
    try:
        _find_duplicate_candidates(db, source, questions, metadata.get("subject_id"))
        db.commit()
        db.refresh(stage)
        return stage
    except Exception:
        db.rollback()
        if created_file:
            (DATA_DIR / raw_path).unlink(missing_ok=True)
        raise
