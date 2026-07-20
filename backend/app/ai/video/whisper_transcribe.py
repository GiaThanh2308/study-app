"""
Dùng faster-whisper (bản Whisper tối ưu tốc độ, chạy tốt trên CPU) để nghe audio
trong video, tách ra thành các đoạn text kèm thời gian bắt đầu/kết thúc.

Cần cài ffmpeg trên máy (faster-whisper dùng ffmpeg để đọc audio từ file video).
Tải ffmpeg tại: https://www.gyan.dev/ffmpeg/builds/ (bản "essentials", giải nén,
thêm đường dẫn thư mục bin vào biến môi trường PATH của Windows).

Model size ảnh hưởng trực tiếp tốc độ/độ chính xác — với máy không GPU, nên dùng
"base" hoặc "small". Máy có GPU xịn (dùng để quét dữ liệu) có thể dùng "medium"
hoặc "large-v3" để chính xác hơn nhiều, đặc biệt với tiếng Việt.
"""
from faster_whisper import WhisperModel

# Đổi giá trị này tùy cấu hình máy:
# - Máy không GPU (CPU): "base" hoặc "small" — cân bằng tốc độ, đủ dùng
# - Máy có GPU xịn: "medium" hoặc "large-v3" — chính xác cao, đặc biệt thuật ngữ chuyên ngành
WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"        # đổi thành "cuda" nếu máy có GPU NVIDIA + cài đúng driver
WHISPER_COMPUTE_TYPE = "int8"  # int8 nhẹ nhất cho CPU; máy GPU nên dùng "float16"

_model_cache = None


def _get_model() -> WhisperModel:
    """Load model 1 lần, dùng lại cho các lần gọi sau (tránh load lại tốn thời gian)."""
    global _model_cache
    if _model_cache is None:
        _model_cache = WhisperModel(
            WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE
        )
    return _model_cache


def transcribe_video(video_path: str, progress_callback=None) -> list[dict]:
    """
    Trả về danh sách đoạn: [{"start": 12.5, "end": 18.2, "text": "..."}, ...]
    start/end tính bằng giây.
    progress_callback(current_seconds, total_seconds) được gọi định kỳ nếu có.
    """
    model = _get_model()
    segments, info = model.transcribe(video_path, language="vi", beam_size=5)

    total_duration = info.duration
    results = []
    for seg in segments:
        results.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
        if progress_callback:
            progress_callback(seg.end, total_duration)

    return results


def format_timestamp(seconds: float) -> str:
    """Chuyển giây thành định dạng mm:ss để hiển thị (VD: 03:41)."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
