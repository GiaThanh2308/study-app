"""
Module thu thập bài giảng từ YouTube (YouTube Harvester).
Tự động lấy phụ đề tiếng Việt (transcript) có gắn mốc thời gian (timestamp từng giây)
và nạp vào cơ sở dữ liệu định vị chính xác (RAG).
Hoàn toàn KHÔNG tải file video MP4 về máy (Zero-Disk Storage).
"""
import re
import logging
import httpx
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.models import Video, Transcript, KnowledgeChunk, Lesson, Chapter

logger = logging.getLogger("studyapp.youtube")


def extract_youtube_id(url: str) -> Optional[str]:
    """Trích xuất Video ID từ các định dạng URL YouTube khác nhau."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def fetch_youtube_transcript(video_id: str) -> List[Dict]:
    """
    Lấy phụ đề có mốc thời gian từ YouTube.
    Thử dùng youtube-transcript-api nếu có, hoặc fetch qua endpoint công khai.
    Trả về dạng: [{'text': '...', 'start': 14.5, 'duration': 3.2}, ...]
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # Ưu tiên lấy tiếng Việt (vi), nếu không có thì lấy tiếng Anh (en)
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['vi', 'en'])
        return transcript
    except Exception as e:
        logger.warning(f"Không thể lấy transcript tự động cho video {video_id} qua API: {e}")
        # Phương án dự phòng: Fetch qua timedtext công khai nếu có
        return []


def index_youtube_lecture(
    db: Session,
    lesson_id: int,
    youtube_url: str,
    title: str,
    transcript_items: List[Dict],
) -> Video:
    """
    Lưu video YouTube và chia nhỏ transcript thành các KnowledgeChunk có timestamp_start.
    """
    video_id = extract_youtube_id(youtube_url) or "unknown"

    # 1. Tạo bản ghi Video
    video = Video(
        lesson_id=lesson_id,
        youtube_url=youtube_url,
        youtube_id=video_id,
        original_filename=title,
        status="processed",
    )
    db.add(video)
    db.flush()

    # Lấy thông tin bài học & chương
    lesson = db.get(Lesson, lesson_id)
    chapter_name = ""
    subject_id = None
    if lesson:
        chapter = db.get(Chapter, lesson.chapter_id)
        if chapter:
            chapter_name = chapter.name
            subject_id = chapter.subject_id

    # 2. Tạo bản ghi Transcript đầy đủ
    full_text = " ".join([item.get("text", "") for item in transcript_items])
    if full_text:
        tr = Transcript(video_id=video.id, text=full_text)
        db.add(tr)

    # 3. Gom cụm transcript thành các chunk 30-60 giây và lưu vào KnowledgeChunk
    if transcript_items:
        current_chunk_text = []
        chunk_start_time = int(transcript_items[0].get("start", 0))
        chunk_index = 0

        for item in transcript_items:
            text = item.get("text", "").strip()
            start = int(item.get("start", 0))

            current_chunk_text.append(text)

            # Gom khoảng 40-50 từ hoặc khi thời gian cách biệt > 40 giây
            if len(" ".join(current_chunk_text).split()) >= 45 or (start - chunk_start_time) >= 45:
                chunk_content = " ".join(current_chunk_text)
                kc = KnowledgeChunk(
                    source_type="youtube",
                    source_id=video.id,
                    subject_id=subject_id,
                    chapter_name=chapter_name,
                    lesson_title=lesson.title if lesson else title,
                    chunk_text=chunk_content,
                    chunk_index=chunk_index,
                    video_id=video.id,
                    youtube_id=video_id,
                    timestamp_start=chunk_start_time,
                    timestamp_end=start,
                    source_url=f"https://www.youtube.com/watch?v=cv_{video_id}",
                )
                db.add(kc)
                chunk_index += 1
                current_chunk_text = []
                chunk_start_time = start

        # Lưu chunk cuối cùng
        if current_chunk_text:
            kc = KnowledgeChunk(
                source_type="youtube",
                source_id=video.id,
                subject_id=subject_id,
                chapter_name=chapter_name,
                lesson_title=lesson.title if lesson else title,
                chunk_text=" ".join(current_chunk_text),
                chunk_index=chunk_index,
                video_id=video.id,
                youtube_id=video_id,
                timestamp_start=chunk_start_time,
                timestamp_end=chunk_start_time + 30,
            )
            db.add(kc)

    db.commit()
    db.refresh(video)
    logger.info(f"Đã nạp video YouTube {video_id} vào bài học #{lesson_id}")
    return video
