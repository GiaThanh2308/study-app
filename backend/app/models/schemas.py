from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


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
    rag_status: str
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    lesson_id: Optional[int]
    subject_id: Optional[int]
    doc_type: str
    file_path: str
    original_filename: Optional[str]
    rag_status: str
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


class LessonTree(LessonOut):
    videos: List[VideoOut] = []
    documents: List[DocumentOut] = []


class ChapterTree(ChapterOut):
    lessons: List[LessonTree] = []


class SubjectTree(SubjectOut):
    chapters: List[ChapterTree] = []


# ---------- Luyện tập / Quiz ----------
class AnswerCreate(BaseModel):
    content: str
    is_correct: bool = False


class AnswerOut(AnswerCreate):
    id: int
    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    subject_id: int
    content: str
    question_type: str = "mcq"
    difficulty: str = "medium"
    explanation: Optional[str] = None
    answers: List[AnswerCreate] = []


class QuestionOut(BaseModel):
    id: int
    subject_id: int
    content: str
    question_type: str
    difficulty: str
    source: str
    explanation: Optional[str]
    answers: List[AnswerOut] = []
    model_config = {"from_attributes": True}


class SubmitAnswerRequest(BaseModel):
    question_id: int
    answer_id: int


class SubmitAnswerResult(BaseModel):
    is_correct: bool
    correct_answer_id: int
    explanation: Optional[str] = None


# ---------- Flashcard ----------
class FlashcardCreate(BaseModel):
    subject_id: int
    front: str
    back: str


class FlashcardOut(FlashcardCreate):
    id: int
    review_count: int
    interval_days: int
    next_review_date: Optional[datetime]
    model_config = {"from_attributes": True}


class FlashcardReviewRequest(BaseModel):
    quality: int  # 0-5, người dùng tự đánh giá độ nhớ (0=quên hết, 5=nhớ rất rõ)
# ---------- Tạo đề thi AI (chuẩn cấu trúc THPT) ----------
class ExamGenerateRequest(BaseModel):
    subject_id: int
    part1_count: int = 12
    part2_count: int = 4
    part3_count: int = 6


class ExamQuestionOut(BaseModel):
    id: int
    part: int
    content: str
    question_type: str
    answers: List[AnswerOut] = []  # part1: 4 đáp án; part2: 4 ý (is_correct luôn trả False khi chưa nộp)
    model_config = {"from_attributes": True}


class ExamOut(BaseModel):
    id: int
    subject_id: int
    title: str
    source_files: List[str] = []
    part1: List[ExamQuestionOut] = []
    part2: List[ExamQuestionOut] = []
    part3: List[ExamQuestionOut] = []


class ExamSubmitRequest(BaseModel):
    mcq_answers: dict[int, int] = {}
    truefalse_answers: dict[int, dict[int, bool]] = {}
    short_answers: dict[int, str] = {}


class ExamResultItem(BaseModel):
    question_id: int
    part: int
    is_correct: Optional[bool] = None
    earned_points: float
    max_points: float
    correct_display: str
    explanation: Optional[str] = None


class ExamSubmitResult(BaseModel):
    total_score: float
    part1_score: float
    part2_score: float
    part3_score: float
    details: List[ExamResultItem]


class ExamSummary(BaseModel):
    id: int
    title: str
    subject_id: int
    created_at: Optional[datetime]
    total_questions: int
    best_score: Optional[float] = None