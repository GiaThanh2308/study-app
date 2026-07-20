"""
Gộp các đoạn transcript nhỏ (mỗi câu Whisper nhận diện) thành các chunk lớn hơn,
đủ dài để embedding hiệu quả, nhưng vẫn giữ được mốc thời gian bắt đầu để trích dẫn.
"""

CHUNK_DURATION_SECONDS = 60  # mỗi chunk gộp khoảng 60 giây transcript


def chunk_transcript(segments: list[dict], chunk_duration: int = CHUNK_DURATION_SECONDS) -> list[dict]:
    """
    segments: [{"start": 12.5, "end": 18.2, "text": "..."}, ...] (từ Whisper)
    Trả về: [{"text": "...", "start_time": 0}, ...] — start_time là giây bắt đầu của chunk,
    dùng để hiển thị "phút mấy" khi trích dẫn.
    """
    if not segments:
        return []

    chunks = []
    current_text = []
    current_start = segments[0]["start"]

    for seg in segments:
        current_text.append(seg["text"])
        if seg["end"] - current_start >= chunk_duration:
            chunks.append({
                "text": " ".join(current_text).strip(),
                "start_time": current_start,
            })
            current_text = []
            current_start = seg["end"]

    # Đoạn còn dư ở cuối
    if current_text:
        chunks.append({
            "text": " ".join(current_text).strip(),
            "start_time": current_start,
        })

    return [c for c in chunks if c["text"]]
