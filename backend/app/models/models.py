from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)      # "Toán", "Văn", "Lý", "Hóa"
    icon = Column(String, nullable=True)

    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")


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
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)  # giây
    status = Column(String, default="pending")  # pending | processed
    rag_status = Column(String, default="pending")  # pending | processing | ready | error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    file_path = Column(String, nullable=True)   # đường dẫn file .srt gốc nếu import sẵn
    text = Column(Text, nullable=True)

    video = relationship("Video", back_populates="transcript")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    doc_type = Column(String, default="pdf")   # pdf | exam
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    rag_status = Column(String, default="pending")  # pending | processing | ready | error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="documents")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)   # "user" hoặc "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("Question", back_populates="answers")


class StudyHistory(Base):
    __tablename__ = "study_history"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("Question")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    front = Column(Text, nullable=False)   # mặt trước: câu hỏi/thuật ngữ
    back = Column(Text, nullable=False)    # mặt sau: đáp án/giải thích
    review_count = Column(Integer, default=0)
    ease_factor = Column(Integer, default=250)  # dùng cho thuật toán lặp lại ngắt quãng, x100 (VD 250 = 2.5)
    interval_days = Column(Integer, default=1)   # số ngày tới lần ôn tiếp theo
    next_review_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject")
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    content = Column(Text, nullable=False)
    question_type = Column(String, default="mcq")  # mcq | truefalse | short_answer | essay
    difficulty = Column(String, default="medium")
    source = Column(String, default="manual")
    topic = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    correct_answer_text = Column(Text, nullable=True)  # đáp án đúng cho câu "trả lời ngắn"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    subject = relationship("Subject")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")

# (Answer, StudyHistory, Flashcard giữ nguyên như cũ)

class ExamPaper(Base):
    __tablename__ = "exam_papers"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String, nullable=False)
    source_files = Column(Text, nullable=True)
    part1_count = Column(Integer, default=12)
    part2_count = Column(Integer, default=4)
    part3_count = Column(Integer, default=6)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    subject = relationship("Subject")
    items = relationship("ExamItem", back_populates="exam", cascade="all, delete-orphan", order_by="ExamItem.order_index")
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")

class ExamItem(Base):
    __tablename__ = "exam_items"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exam_papers.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    part = Column(Integer, nullable=False)  # 1, 2, 3
    order_index = Column(Integer, default=0)
    exam = relationship("ExamPaper", back_populates="items")
    question = relationship("Question")

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exam_papers.id"), nullable=False)
    score = Column(Integer, nullable=False)  # x100
    part1_score = Column(Integer, default=0)
    part2_score = Column(Integer, default=0)
    part3_score = Column(Integer, default=0)
    detail_json = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    exam = relationship("ExamPaper", back_populates="attempts")