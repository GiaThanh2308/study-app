"""
RAG (Retrieval-Augmented Generation) engine định vị chính xác (Smart Precision RAG).
Tìm kiếm kiến thức trong kho dữ liệu app (YouTube timestamp, transcript, PDF page, Word)
rồi trả kết quả kèm tọa độ vị trí chính xác (phút:giây, trang số) để trình phát giao diện nhảy đến đúng vị trí.
"""
import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.models import KnowledgeChunk, Video, Subject, Document

logger = logging.getLogger("studyapp.rag")

CHUNK_SIZE = 450
CHUNK_OVERLAP = 80


def chunk_text(content: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Chia text dài thành các đoạn nhỏ có overlap."""
    if not content or not content.strip():
        return []

    content = content.strip()
    if len(content) <= chunk_size:
        return [content]

    chunks = []
    start = 0
    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]
        if end < len(content):
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            cut_point = max(last_period, last_newline)
            if cut_point > chunk_size // 2:
                chunk = chunk[: cut_point + 1]
                end = start + cut_point + 1

        chunks.append(chunk.strip())
        start = end - overlap
        if start >= len(content):
            break

    return [c for c in chunks if c]


def index_content(
    db: Session,
    content: str,
    source_type: str,
    source_id: int,
    subject_id: Optional[int] = None,
    chapter_name: Optional[str] = None,
    lesson_title: Optional[str] = None,
    video_id: Optional[int] = None,
    youtube_id: Optional[str] = None,
    page_number: Optional[int] = None,
    timestamp_start: Optional[int] = None,
    source_url: Optional[str] = None,
) -> int:
    """Chia nhỏ nội dung thành chunks có metadata định vị và lưu vào KnowledgeChunk."""
    if not content or not content.strip():
        return 0

    chunks = chunk_text(content)
    count = 0
    for idx, chunk in enumerate(chunks):
        kc = KnowledgeChunk(
            source_type=source_type,
            source_id=source_id,
            subject_id=subject_id,
            chapter_name=chapter_name,
            lesson_title=lesson_title,
            chunk_text=chunk,
            chunk_index=idx,
            video_id=video_id,
            youtube_id=youtube_id,
            page_number=page_number,
            timestamp_start=timestamp_start,
            source_url=source_url,
        )
        db.add(kc)
        count += 1

    db.commit()
    return count


def search_knowledge(db: Session, query: str, limit: int = 4) -> List[dict]:
    """
    Tìm kiếm kiến thức phù hợp nhất kèm tọa độ vị trí:
    - YouTube / Video: phút, giây
    - PDF: số trang
    """
    if not query or not query.strip():
        return []

    stopwords = {"là", "và", "của", "cho", "trong", "có", "được", "này", "với",
                 "các", "một", "những", "đã", "để", "khi", "thì", "nhưng", "hay",
                 "hoặc", "nếu", "về", "từ", "theo", "như", "tại", "bị", "đang",
                 "sẽ", "không", "bao", "nhiêu", "nào", "gì", "sao", "vì", "do",
                 "nên", "cần", "phải", "mà", "cũng", "rất", "hơn", "nhất", "hãy"}

    words = [w.strip() for w in re.split(r'\s+', query.lower()) if w.strip() and w.lower() not in stopwords]
    if not words:
        words = query.lower().split()[:5]

    all_chunks = db.query(KnowledgeChunk).all()
    scored = []

    for chunk in all_chunks:
        chunk_lower = chunk.chunk_text.lower()
        score = 0
        for word in words:
            count = chunk_lower.count(word)
            if count > 0:
                score += count * 2
                if chunk_lower.startswith(word):
                    score += 3

        if chunk.chapter_name:
            for word in words:
                if word in chunk.chapter_name.lower():
                    score += 6
        if chunk.lesson_title:
            for word in words:
                if word in chunk.lesson_title.lower():
                    score += 8

        if score > 0:
            scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for chunk, score in scored[:limit]:
        video_path = None
        youtube_id = chunk.youtube_id

        if chunk.video_id:
            video = db.get(Video, chunk.video_id)
            if video:
                video_path = video.file_path
                if not youtube_id:
                    youtube_id = video.youtube_id

        subject_name = None
        if chunk.subject_id:
            subject = db.get(Subject, chunk.subject_id)
            if subject:
                subject_name = subject.name

        results.append({
            "chunk_text": chunk.chunk_text,
            "source_type": chunk.source_type,
            "subject_name": subject_name,
            "chapter_name": chunk.chapter_name,
            "lesson_title": chunk.lesson_title,
            "video_id": chunk.video_id,
            "video_path": video_path,
            "youtube_id": youtube_id,
            "timestamp_start": chunk.timestamp_start or 0,
            "page_number": chunk.page_number,
            "relevance_score": score,
        })

    return results


def build_rag_prompt(query: str, rag_results: List[dict]) -> str:
    """Xây dựng prompt cho AI với context định vị từ kho kiến thức."""
    if not rag_results:
        return query

    context_parts = []
    for i, r in enumerate(rag_results, 1):
        header = f"[Tài liệu {i}]"
        if r.get("subject_name"):
            header += f" Môn: {r['subject_name']}"
        if r.get("chapter_name"):
            header += f" | Chương: {r['chapter_name']}"
        if r.get("lesson_title"):
            header += f" | Bài: {r['lesson_title']}"
        if r.get("page_number"):
            header += f" (Trang {r['page_number']})"
        if r.get("timestamp_start"):
            mins = r['timestamp_start'] // 60
            secs = r['timestamp_start'] % 60
            header += f" (Đoạn video tại {mins}:{secs:02d})"
            
        context_parts.append(f"{header}\n{r['chunk_text']}")

    context = "\n\n".join(context_parts)

    prompt = f"""Dựa trên kiến thức trích xuất từ kho học liệu ôn thi:

{context}

Câu hỏi của học sinh: {query}

Hãy giải thích chi tiết, ngắn gọn, dễ hiểu nhất cho học sinh lớp 12. Nêu rõ công thức và phương pháp giải nếu có.
Hệ thống sẽ tự động đính kèm video và trang sách liên quan ở phía dưới câu trả lời của bạn."""

    return prompt
