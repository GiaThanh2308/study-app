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
