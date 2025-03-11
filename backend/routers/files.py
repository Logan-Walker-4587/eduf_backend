from fastapi import APIRouter, Security, File, UploadFile, HTTPException, Depends
from auth0.utils import VerifyToken
from fastapi.responses import FileResponse
import os
from pathlib import Path
from llama_core.core import generate_cards, ingest 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.model import Flash, Base 

auth = VerifyToken()

# Storage directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok = True)

# Database
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
router = APIRouter(prefix="/file", tags=["File"])

@router.post("/upload/{chat_id}")
async def upload_file(chat_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db), security: dict[str, str] = Security(auth.verify)):
    ## Get unique user id from the subject id in the authentication token
    user_id = security["sub"].split("@")[0]
    user_dir = Path(UPLOAD_DIR) / user_id / str(chat_id)
    files_dir = user_dir / "files"

    user_dir.mkdir(parents=True, exist_ok=True)
    files_dir.mkdir(parents=True, exist_ok=True)
    
    file_data = dict()
    for file in files:
        if file.filename is not None:
            file_path = files_dir / file.filename
            with file_path.open("wb") as f:
                f.write(await file.read())
                file_data[file.filename] = file.size

    ## Generate flash cards
    ingest(str(user_dir))
    flash_cards = generate_cards(str(user_dir))

    for i in flash_cards:
        card = Flash(user_id=user_id, chat_id=chat_id, topic_name=i[0], question=i[1], answer=i[2])
        db.add(card)
        db.commit()
        db.refresh(card)

    return file_data

@router.get("/list_files/{chat_id}")
def get_files(chat_id: int, security: dict[str, str] = Security(auth.verify)):
    user_id = security["sub"].split("@")[0]
    user_dir = Path(UPLOAD_DIR) / user_id / str(chat_id) 
    files_dir = user_dir / "files"
    try:
        files = os.listdir(files_dir)
    except:
        raise HTTPException(status_code=404, detail="Chat not found")

    return files

@router.get("/fetch_file/{chat_id}/{file_name}")
def fetch_file(chat_id: int, file_name: str, security: dict[str, str] = Security(auth.verify)):
    user_id = security["sub"].split("@")[0]
    file_path = Path(UPLOAD_DIR) / user_id / str(chat_id) / "files" / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
