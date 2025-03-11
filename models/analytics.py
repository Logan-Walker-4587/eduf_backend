from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FlashcardView(Base):
    __tablename__ = "flashcard_views"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"))
    viewed_at = Column(DateTime, default=datetime.utcnow)

class TestQuestion(Base):
    __tablename__ = "test_questions"
    id = Column(Integer, primary_key=True, index=True)
    test_result_id = Column(Integer, ForeignKey("test_results.id"))
    question_text = Column(String)
    correct_answer = Column(String)
    student_answer = Column(String)
    is_correct = Column(Boolean, default=False)
    topic = Column(String)  # To track which topic this question belongs to
    subtopic = Column(String)  # For more granular topic tracking
    test_result = relationship("TestResult", back_populates="questions")

class TestResult(Base):
    __tablename__ = "test_results"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    test_id = Column(Integer, ForeignKey("tests.id"))
    score = Column(Float)
    completed_at = Column(DateTime, default=datetime.utcnow)
    ai_feedback = Column(JSON)  # Structured feedback from Groq
    questions = relationship("TestQuestion", back_populates="test_result")
    
    # Detailed analytics
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    topics_summary = Column(JSON)  # Performance by topic
    time_taken = Column(Integer)  # Time taken in seconds

class StudentAnalytics(Base):
    __tablename__ = "student_analytics"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    total_flashcards_viewed = Column(Integer, default=0)
    total_tests_taken = Column(Integer, default=0)
    average_test_score = Column(Float, default=0.0)
    weak_topics = Column(JSON)  # List of topics needing improvement
    strong_topics = Column(JSON)  # List of mastered topics
    learning_streak = Column(Integer, default=0)  # Consecutive days of activity
    last_activity = Column(DateTime, default=datetime.utcnow)
    historical_performance = Column(JSON)  # Monthly/weekly performance trends
