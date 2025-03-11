from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

# Chat Model
class Chat(Base):
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(primary_key=True)
    chat_name: Mapped[str] = mapped_column(nullable=False)
    owner_id: Mapped[str] = mapped_column(index=True)  # Auth0 user ID
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    flash: Mapped[list["Flash"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    ques: Mapped[list["Questions"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    quiz: Mapped[list["Quiz"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    
# Flash Cards
class Flash(Base):
    __tablename__ = "cards"

    flash_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"))
    topic_name: Mapped[str] = mapped_column(nullable=False)
    question: Mapped[str] = mapped_column(nullable=False)
    answer: Mapped[str] = mapped_column(nullable=False)
    chat: Mapped["Chat"] = relationship(back_populates="flash")

# Questions
class Questions(Base):
    __tablename__ = "questions"

    question_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"))
    question_content: Mapped[str] = mapped_column(nullable=False)
    response: Mapped[str] = mapped_column(nullable=False)
    chat: Mapped["Chat"] = relationship(back_populates="ques")

# Quiz
class Quiz(Base):
    __tablename__ = "quiz"

    question_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"))
    question: Mapped[str] = mapped_column(nullable=False)
    option_a: Mapped[str] = mapped_column(nullable=False)
    option_b: Mapped[str] = mapped_column(nullable=False)
    option_c: Mapped[str] = mapped_column(nullable=False)
    option_d: Mapped[str] = mapped_column(nullable=False)
    correct_answer: Mapped[str] = mapped_column(nullable=False)
    chat: Mapped["Chat"] = relationship(back_populates="quiz")
