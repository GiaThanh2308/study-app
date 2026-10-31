from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)      # "Toán", "Vật lý", "Hóa học"
    icon = Column(String, nullable=True)

    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="subject", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    name = Column(String, nullable=False)
    order = Column(Integer, default=0)

    subject = relationship("Subject", back_populates="chapters")
    lessons = relationship("Lesson", back_populates="chapter", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    chapter = relationship("Chapter", back_populates="lessons")
    videos = relationship("Video", back_populates="lesson", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="lesson", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    file_path = Column(String, nullable=True)          # Đường dẫn file local (nếu có)
    youtube_url = Column(String, nullable=True)        # URL YouTube hoặc Video online
    youtube_id = Column(String, nullable=True)         # ID của video trên YouTube
    original_filename = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)          # giây
    status = Column(String, default="pending")          # pending | processed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    file_path = Column(String, nullable=True)
    text = Column(Text, nullable=True)

    video = relationship("Video", back_populates="transcript")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    doc_type = Column(String, default="pdf")   # pdf | docx | exam | web
    file_path = Column(String, nullable=False)
    source_url = Column(String, nullable=True) # Nguồn link trên internet nếu cào về
    original_filename = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    text_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="documents")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)   # "user" hoặc "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===================== HỆ THỐNG ĐỀ THI =====================

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=90)
    exam_type = Column(String, default="practice")  # practice | mock | national | image_imported
    source_origin = Column(String, nullable=True)   # "Sở GD&ĐT Hà Nội", "THPT Chuyên Lam Sơn", "web_harvester"
    
    # Thông tin nguồn gốc & chuẩn chương trình (Authentic Provenance)
    province = Column(String, nullable=True)            # Tỉnh / Thành phố (VD: Hà Nội, Nghệ An, Thanh Hóa)
    school_or_dept = Column(String, nullable=True)      # Trường THPT hoặc Sở GD&ĐT ra đề
    exam_year = Column(Integer, default=2025)           # Năm thi
    exam_round = Column(String, nullable=True)          # Lần thi (Lần 1, Lần 2, Đề tham khảo...)
    curriculum_standard = Column(String, default="GDPT 2018") # GDPT 2018 (Chương trình mới)
    is_authentic = Column(Boolean, default=True)        # Đề thật nguyên bản 100%

    total_questions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject", back_populates="exams")
    questions = relationship("ExamQuestion", back_populates="exam",
                             cascade="all, delete-orphan",
                             order_by="ExamQuestion.question_number")
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_type = Column(String, default="multiple_choice")  # multiple_choice | true_false | short_answer
    question_text = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)                  # Nếu câu hỏi có hình vẽ
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    correct_answer = Column(String, nullable=False)            # A / B / C / D | T,F,T,F | 3.5
    explanation = Column(Text, nullable=True)
    topic_tag = Column(String, nullable=True)

    exam = relationship("Exam", back_populates="questions")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    total_correct = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    status = Column(String, default="in_progress")

    exam = relationship("Exam", back_populates="attempts")
    answers = relationship("UserAnswer", back_populates="attempt", cascade="all, delete-orphan")


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("exam_questions.id"), nullable=False)
    selected_answer = Column(String(1), nullable=True)
    is_correct = Column(Boolean, default=False)

    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("ExamQuestion")


# ===================== KHO KIẾN THỨC ĐỊNH VỊ CHÍNH XÁC (SMART PRECISION RAG) =====================

class KnowledgeChunk(Base):
    """
    Một đoạn text nhỏ có tọa độ vật lý chính xác:
    - Nếu là video (YouTube/Local): có timestamp_start, timestamp_end (giây)
    - Nếu là PDF: có page_number (trang)
    - Nếu là Word: có section_title (tiêu đề mục)
    """
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, nullable=False)   # youtube | video_transcript | pdf | docx | web
    source_id = Column(Integer, nullable=True)      # ID của Video hoặc Document gốc
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    chapter_name = Column(String, nullable=True)
    lesson_title = Column(String, nullable=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    
    # Định vị chính xác
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    youtube_id = Column(String, nullable=True)      # Mã ID video trên YouTube
    timestamp_start = Column(Integer, nullable=True) # Giây bắt đầu (vd: 865 = 14m25s)
    timestamp_end = Column(Integer, nullable=True)   # Giây kết thúc
    page_number = Column(Integer, nullable=True)     # Trang PDF (vd: trang 12)
    section_title = Column(String, nullable=True)   # Mục trong tài liệu Word
    source_url = Column(String, nullable=True)      # URL gốc trên internet

    created_at = Column(DateTime(timezone=True), server_default=func.now())
