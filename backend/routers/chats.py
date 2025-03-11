from fastapi import APIRouter, Security, Depends, HTTPException
from auth0.utils import VerifyToken
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker, Session
from models.model import Chat, Base
from pathlib import Path

router = APIRouter(prefix="/chats", tags=["Chats"])
auth = VerifyToken()

UPLOAD_DIR = "uploads"
DATABASE_URL = "sqlite:///./chats.db"

# Initialize Database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create a new chat
@router.post("/new")
def create_chat(chat_name: str, db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    chat = Chat(chat_name=chat_name, owner_id=security["sub"].split("@")[0])
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return {"chat_id": chat.chat_id, "chat_name": chat.chat_name, "created_at": chat.created_at}

# Get all chats for the logged-in user
@router.get("")
def get_chats(db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    chats = db.query(Chat).filter(Chat.owner_id == security["sub"].split("@")[0]).all()
    if len(chats) == 0:
        raise HTTPException(status_code=404, detail="Not Found")
    return chats

@router.delete("/delete/{chat_id}")
def delete_chat(chat_id: int, db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    user_id = security["sub"].split("@")[0]

    # Delete uploaded files if any exists
    path = Path(UPLOAD_DIR) / user_id / str(chat_id) 
    if path.exists():
        path.unlink()

    statement = delete(Chat).where(Chat.chat_id == chat_id).where(Chat.owner_id == user_id)
    result = db.execute(statement)
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    return { "message": "The chat has been deleted"}
