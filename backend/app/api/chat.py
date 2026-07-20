from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import models
from app.ai.ollama_client import chat_stream, check_ollama_available

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.get("/chat/status")
async def chat_status():
    available = await check_ollama_available()
    return {"ollama_running": available}


@router.get("/chat/history")
def chat_history(db: Session = Depends(get_db)):
    messages = db.query(models.ChatMessage).order_by(models.ChatMessage.id).all()
    return [{"role": m.role, "content": m.content} for m in messages]


@router.post("/chat/send")
async def chat_send(payload: ChatRequest, db: Session = Depends(get_db)):
    # Lưu tin nhắn người dùng
    user_msg = models.ChatMessage(role="user", content=payload.message)
    db.add(user_msg)
    db.commit()

    # Lấy toàn bộ lịch sử để model có ngữ cảnh (giới hạn 20 tin gần nhất cho nhẹ)
    history = (
        db.query(models.ChatMessage)
        .order_by(models.ChatMessage.id.desc())
        .limit(20)
        .all()
    )
    history.reverse()
    messages = [{"role": m.role, "content": m.content} for m in history]

    async def event_generator():
        full_response = ""
        async for chunk in chat_stream(messages):
            full_response += chunk
            yield chunk

        # Sau khi stream xong, lưu câu trả lời đầy đủ vào DB
        assistant_msg = models.ChatMessage(role="assistant", content=full_response)
        db.add(assistant_msg)
        db.commit()

    return StreamingResponse(event_generator(), media_type="text/plain")
