from fastapi import APIRouter, Security, File, UploadFile, HTTPException, Depends
from auth0.utils import VerifyToken
from pathlib import Path
from llama_core.core import query, generate_quiz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.model import Flash, Base, Questions, Quiz


UPLOAD_DIR = "uploads"
# Database
DATABASE_URL = "sqlite:///./chats.db"

router = APIRouter(prefix="/rag", tags=["RAG"])

# Initialize Database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Tables
Base.metadata.create_all(bind=engine)
auth = VerifyToken()

# Dependency to get DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/cards/{chat_id}")
def fetch_cards(chat_id: str, db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    ## BIG PROBLEM RIGHT HERE
    user_id = security["sub"].split("@")[0]
    cards = db.query(Flash).filter(Flash.chat_id == chat_id and Flash.user_id == user_id).all()
    return cards

@router.get("/{chat_id}/")
def query_files(chat_id: str, q: str, db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    ## BIG PROBLEM RIGHT HERE
    user_id = security["sub"].split("@")[0]
    user_dir = Path(UPLOAD_DIR) / user_id / str(chat_id) 
    response =  str(query(str(user_dir), q))
    question = Questions(user_id=user_id, chat_id=chat_id, question_content=q, response=response) 
    db.add(question)
    db.commit()
    db.refresh(question)

    return response

@router.get("/queries/{chat_id}")
def fetch_all_queries(chat_id: str, db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    user_id = security["sub"].split("@")[0]
    questions = db.query(Questions).filter(Questions.user_id == user_id and Questions.chat_id == chat_id).all()
    return questions

@router.get("/summarize/{chat_id}/")
def summarise(chat_id: str, security: dict[str, str] = Security(auth.verify)):
    user_id = security["sub"].split("@")[0]
    user_dir = Path(UPLOAD_DIR) / user_id / str(chat_id) 
    response =  str(query(str(user_dir), "Generate a summary of all the documents"))
    return response

@router.get("/generate_quiz/{chat_id}/")
def generate_a_quiz(chat_id: str, security: dict[str, str] = Security(auth.verify)):
    user_id = security["sub"].split("@")[0]
    user_dir = Path(UPLOAD_DIR) / str(user_id) / str(chat_id) 
    quiz = generate_quiz(str(user_dir))
    return quiz
