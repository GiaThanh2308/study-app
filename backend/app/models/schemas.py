from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ===================== MÔN / CHƯƠNG / BÀI =====================

class SubjectCreate(BaseModel):
    name: str
    icon: Optional[str] = None


class SubjectOut(SubjectCreate):
    id: int
    model_config = {"from_attributes": True}


class ChapterCreate(BaseModel):
    subject_id: int
    name: str
    order: int = 0


class ChapterOut(ChapterCreate):
    id: int
    model_config = {"from_attributes": True}


class LessonCreate(BaseModel):
    chapter_id: int
    title: str
    description: Optional[str] = None


class LessonOut(LessonCreate):
    id: int
    model_config = {"from_attributes": True}


class VideoOut(BaseModel):
    id: int
    lesson_id: int
    file_path: str
    original_filename: Optional[str]
    status: str
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    lesson_id: Optional[int]
    subject_id: Optional[int]
    doc_type: str
    file_path: str
    original_filename: Optional[str]
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


class LessonTree(LessonOut):
    videos: List[VideoOut] = []
    documents: List[DocumentOut] = []


class ChapterTree(ChapterOut):
    lessons: List[LessonTree] = []


class SubjectTree(SubjectOut):
    chapters: List[ChapterTree] = []


# ===================== ĐỀ THI =====================

class QuestionCreate(BaseModel):
    question_number: int
    question_type: Optional[str] = "multiple_choice"  # multiple_choice | true_false | short_answer
    question_text: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: str  # A/B/C/D hoặc T,F,T,F hoặc số (vd: "2.5")
    explanation: Optional[str] = None
    topic_tag: Optional[str] = None


class QuestionOut(QuestionCreate):
    id: int
    exam_id: int
    model_config = {"from_attributes": True}


class ExamCreate(BaseModel):
    subject_id: int
    title: str
    description: Optional[str] = None
    duration_minutes: int = 90
    exam_type: str = "practice"  # practice | mock | national
    province: Optional[str] = None
    school_or_dept: Optional[str] = None
    exam_year: Optional[int] = 2025
    exam_round: Optional[str] = None
    curriculum_standard: Optional[str] = "GDPT 2018"
    is_authentic: Optional[bool] = True
    questions: List[QuestionCreate] = []


class ExamOut(BaseModel):
    id: int
    subject_id: int
    title: str
    description: Optional[str]
    duration_minutes: int
    exam_type: str
    total_questions: int
    province: Optional[str] = None
    school_or_dept: Optional[str] = None
    exam_year: Optional[int] = 2025
    exam_round: Optional[str] = None
    curriculum_standard: Optional[str] = "GDPT 2018"
    is_authentic: Optional[bool] = True
    source_origin: Optional[str] = None
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


class ExamDetail(ExamOut):
    questions: List[QuestionOut] = []


class AnswerSubmit(BaseModel):
    question_id: int
    selected_answer: Optional[str] = None  # A/B/C/D hoặc null


class AttemptSubmit(BaseModel):
    exam_id: int
    answers: List[AnswerSubmit]


class UserAnswerOut(BaseModel):
    question_id: int
    selected_answer: Optional[str]
    is_correct: bool
    model_config = {"from_attributes": True}


class AttemptOut(BaseModel):
    id: int
    exam_id: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    score: Optional[float]
    total_correct: int
    total_questions: int
    status: str
    model_config = {"from_attributes": True}


class AttemptDetail(AttemptOut):
    answers: List[UserAnswerOut] = []
    exam: Optional[ExamOut] = None


# ===================== THỐNG KÊ =====================

class SubjectStats(BaseModel):
    subject_id: int
    subject_name: str
    total_exams: int
    completed_exams: int
    remaining_exams: int
    average_score: Optional[float]
    best_score: Optional[float]
    total_questions_done: int
    total_correct: int
    accuracy_percent: Optional[float]


class OverallStats(BaseModel):
    total_subjects: int
    total_chapters: int
    total_lessons: int
    total_videos: int
    total_documents: int
    total_exams: int
    total_attempts: int
    completed_attempts: int
    overall_average_score: Optional[float]
    subjects: List[SubjectStats]


# ===================== RAG / CHAT =====================

class ChatRequest(BaseModel):
    message: str


class RAGResult(BaseModel):
    chunk_text: str
    source_type: str
    subject_name: Optional[str] = None
    chapter_name: Optional[str] = None
    lesson_title: Optional[str] = None
    video_id: Optional[int] = None
    video_path: Optional[str] = None
    relevance_score: float = 0.0
