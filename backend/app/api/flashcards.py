from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import models, schemas

router = APIRouter()


@router.post("/flashcards", response_model=schemas.FlashcardOut)
def create_flashcard(payload: schemas.FlashcardCreate, db: Session = Depends(get_db)):
    card = models.Flashcard(**payload.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.get("/flashcards", response_model=list[schemas.FlashcardOut])
def list_flashcards(subject_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Flashcard)
    if subject_id:
        query = query.filter(models.Flashcard.subject_id == subject_id)
    return query.all()


@router.get("/flashcards/due", response_model=list[schemas.FlashcardOut])
def get_due_flashcards(subject_id: int | None = None, db: Session = Depends(get_db)):
    """Chỉ trả về thẻ ĐẾN HẠN ôn lại hôm nay (next_review_date <= hiện tại)."""
    now = datetime.now(timezone.utc)
    query = db.query(models.Flashcard).filter(models.Flashcard.next_review_date <= now)
    if subject_id:
        query = query.filter(models.Flashcard.subject_id == subject_id)
    return query.all()


@router.delete("/flashcards/{card_id}")
def delete_flashcard(card_id: int, db: Session = Depends(get_db)):
    card = db.query(models.Flashcard).get(card_id)
    if not card:
        raise HTTPException(404, "Flashcard không tồn tại")
    db.delete(card)
    db.commit()
    return {"ok": True}


@router.post("/flashcards/{card_id}/review", response_model=schemas.FlashcardOut)
def review_flashcard(card_id: int, payload: schemas.FlashcardReviewRequest, db: Session = Depends(get_db)):
    """
    Thuật toán lặp lại ngắt quãng rút gọn từ SM-2:
    - quality (0-5): người dùng tự đánh giá độ nhớ khi lật thẻ
    - quality < 3 (quên/mơ hồ): reset về ôn lại sau 1 ngày
    - quality >= 3 (nhớ tốt): khoảng cách lần ôn tiếp theo tăng dần (nhân với ease_factor)
    """
    card = db.query(models.Flashcard).get(card_id)
    if not card:
        raise HTTPException(404, "Flashcard không tồn tại")

    quality = payload.quality
    card.review_count += 1

    if quality < 3:
        card.interval_days = 1
    else:
        if card.review_count <= 1:
            card.interval_days = 1
        elif card.review_count == 2:
            card.interval_days = 6
        else:
            card.interval_days = round(card.interval_days * (card.ease_factor / 100))

        # Điều chỉnh ease_factor theo công thức SM-2 (giữ trong khoảng hợp lý, x100 để lưu dạng int)
        new_ease = card.ease_factor + (10 - (5 - quality) * (8 + (5 - quality) * 2))
        card.ease_factor = max(130, new_ease)  # không để ease_factor xuống quá thấp

    card.next_review_date = datetime.now(timezone.utc) + timedelta(days=card.interval_days)
    db.commit()
    db.refresh(card)
    return card
