from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
import pandas as pd
import plotly.express as px
from groq import Groq
from datetime import datetime, timedelta
import json
from pydantic import BaseModel

from ..models.analytics import FlashcardView, TestResult, TestQuestion, StudentAnalytics
from ..database import get_db
from ..config import GROQ_API_KEY

router = APIRouter()
groq_client = Groq(api_key=GROQ_API_KEY)

class QuestionSubmission(BaseModel):
    question_text: str
    correct_answer: str
    student_answer: str
    topic: str
    subtopic: str

class TestSubmission(BaseModel):
    questions: List[QuestionSubmission]
    time_taken: int  # in seconds

def generate_ai_insights(questions: List[QuestionSubmission], previous_results: List[TestResult] = None):
    # Prepare detailed analysis of current test
    correct_count = sum(1 for q in questions if q.student_answer == q.correct_answer)
    total_questions = len(questions)
    score = (correct_count / total_questions) * 100
    
    # Group questions by topic
    topic_performance = {}
    for q in questions:
        if q.topic not in topic_performance:
            topic_performance[q.topic] = {"correct": 0, "total": 0, "questions": []}
        
        is_correct = q.student_answer == q.correct_answer
        topic_performance[q.topic]["correct"] += 1 if is_correct else 0
        topic_performance[q.topic]["total"] += 1
        topic_performance[q.topic]["questions"].append({
            "question": q.question_text,
            "correct_answer": q.correct_answer,
            "student_answer": q.student_answer,
            "is_correct": is_correct
        })

    # Prepare historical context if available
    historical_context = ""
    if previous_results:
        avg_score = sum(r.score for r in previous_results) / len(previous_results)
        historical_context = f"\\nHistorical context: Your average score is {avg_score:.1f}%. "
        if score > avg_score:
            historical_context += "You performed above your usual average!"
        else:
            historical_context += "This score is below your usual performance."

    # Create detailed prompt for Groq
    prompt = f"""As an educational AI assistant, analyze this test performance:

Overall Performance:
- Score: {score:.1f}%
- Correct answers: {correct_count}/{total_questions}
- Time taken: {questions[0].time_taken} seconds

Detailed Topic Analysis:
{json.dumps(topic_performance, indent=2)}
{historical_context}

Please provide:
1. Specific strengths and weaknesses based on topic performance
2. Detailed analysis of mistakes made, including common patterns
3. Personalized study recommendations for each weak topic
4. Time management feedback
5. Suggested focus areas for immediate improvement

Format the response in a clear, structured way that's encouraging but direct about areas needing improvement."""

    completion = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    
    return {
        "analysis": completion.choices[0].message.content,
        "topic_performance": topic_performance,
        "score": score,
        "time_taken": questions[0].time_taken
    }

@router.post("/submit-test/{student_id}/{test_id}")
async def submit_test(
    student_id: int,
    test_id: int,
    test_submission: TestSubmission,
    db: Session = Depends(get_db)
):
    # Get previous test results for context
    previous_results = db.query(TestResult).filter(
        TestResult.student_id == student_id
    ).order_by(TestResult.completed_at.desc()).limit(5).all()
    
    # Generate AI insights
    insights = generate_ai_insights(test_submission.questions, previous_results)
    
    # Create test result
    test_result = TestResult(
        student_id=student_id,
        test_id=test_id,
        score=insights["score"],
        ai_feedback=insights,
        total_questions=len(test_submission.questions),
        correct_answers=sum(1 for q in test_submission.questions if q.student_answer == q.correct_answer),
        topics_summary=insights["topic_performance"],
        time_taken=test_submission.time_taken
    )
    db.add(test_result)
    db.flush()  # Get test_result.id
    
    # Add individual questions
    for q in test_submission.questions:
        question = TestQuestion(
            test_result_id=test_result.id,
            question_text=q.question_text,
            correct_answer=q.correct_answer,
            student_answer=q.student_answer,
            is_correct=q.student_answer == q.correct_answer,
            topic=q.topic,
            subtopic=q.subtopic
        )
        db.add(question)
    
    # Update student analytics
    analytics = db.query(StudentAnalytics).filter(
        StudentAnalytics.student_id == student_id
    ).first()
    
    if not analytics:
        analytics = StudentAnalytics(student_id=student_id)
        db.add(analytics)
    
    analytics.total_tests_taken += 1
    analytics.last_activity = datetime.utcnow()
    
    # Update average score
    all_scores = [r.score for r in previous_results] + [insights["score"]]
    analytics.average_test_score = sum(all_scores) / len(all_scores)
    
    # Update weak and strong topics
    topic_strengths = {}
    for topic, data in insights["topic_performance"].items():
        score = (data["correct"] / data["total"]) * 100
        topic_strengths[topic] = score
    
    analytics.weak_topics = [topic for topic, score in topic_strengths.items() if score < 70]
    analytics.strong_topics = [topic for topic, score in topic_strengths.items() if score >= 90]
    
    # Update learning streak
    if analytics.last_activity and (datetime.utcnow() - analytics.last_activity) <= timedelta(days=1):
        analytics.learning_streak += 1
    else:
        analytics.learning_streak = 1
    
    db.commit()
    
    return {
        "status": "success",
        "insights": insights,
        "analytics_summary": {
            "total_tests": analytics.total_tests_taken,
            "average_score": analytics.average_test_score,
            "learning_streak": analytics.learning_streak,
            "weak_topics": analytics.weak_topics,
            "strong_topics": analytics.strong_topics
        }
    }

@router.get("/student-performance/{student_id}")
async def get_student_performance(
    student_id: int,
    db: Session = Depends(get_db)
):
    analytics = db.query(StudentAnalytics).filter(
        StudentAnalytics.student_id == student_id
    ).first()
    
    if not analytics:
        raise HTTPException(status_code=404, detail="Student analytics not found")
    
    # Get recent test results with details
    recent_tests = db.query(TestResult).filter(
        TestResult.student_id == student_id
    ).order_by(TestResult.completed_at.desc()).limit(10).all()
    
    # Create performance chart
    test_data = [{
        "date": test.completed_at,
        "score": test.score,
        "topics": list(test.topics_summary.keys()),
        "time_taken": test.time_taken,
        "insights": test.ai_feedback["analysis"]
    } for test in recent_tests]
    
    if test_data:
        df = pd.DataFrame(test_data)
        fig = px.line(
            df,
            x="date",
            y="score",
            title="Test Score Progression",
            labels={"date": "Date", "score": "Score (%)"}
        )
        performance_chart = fig.to_json()
    else:
        performance_chart = None
    
    return {
        "overall_stats": {
            "total_tests_taken": analytics.total_tests_taken,
            "average_score": analytics.average_test_score,
            "learning_streak": analytics.learning_streak,
            "weak_topics": analytics.weak_topics,
            "strong_topics": analytics.strong_topics,
            "last_activity": analytics.last_activity
        },
        "recent_tests": test_data,
        "performance_chart": performance_chart
    }
