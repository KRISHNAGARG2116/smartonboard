import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RequireEmployee, EmployeeDb
from models.employees import Employee
from models.employee_welcome_event import EmployeeWelcomeEvent
from db.session import tenant_context

router = APIRouter(prefix="/employee/welcome", tags=["Employee Welcome Center"])

@router.get("/welcome-schedule")
def list_welcome_schedule(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve welcome schedule, including orientation and recurring 30/60/90 reviews."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    events = db.scalars(
        select(EmployeeWelcomeEvent)
        .where(EmployeeWelcomeEvent.employee_id == employee.id)
        .order_by(EmployeeWelcomeEvent.scheduled_at.asc())
    ).all()

    return events


@router.get("/welcome-center")
def get_welcome_center_assets(
    current_employee: RequireEmployee,
    db: EmployeeDb,
):
    """Retrieve welcome resources (videos, CEO message, maps, benefits overview, FAQs)."""
    employee = db.scalar(
        select(Employee).where(Employee.user_id == current_employee.id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    # Provide high-quality assets to wow the employee on Day 1
    return {
        "welcome_video_url": "https://assets.smartonboard.com/videos/welcome_2026.mp4",
        "ceo_message": {
            "author": "Elena Vance, CEO",
            "avatar_url": "https://assets.smartonboard.com/images/elena.jpg",
            "message": "Welcome to SmartOnboard! We're thrilled to have you join our mission of building a trusted hiring ecosystem. Your journey starts here, and we're committed to supporting you at every step. Let's make an impact together!"
        },
        "office_map": {
            "building": "HQ South - Floor 4",
            "desk_number": "D-412",
            "map_image_url": "https://assets.smartonboard.com/images/floor4_map.png"
        },
        "benefits_overview_link": "https://assets.smartonboard.com/docs/benefits_guide_2026.pdf",
        "faqs": [
            {
                "question": "What time does orientation start?",
                "answer": "Orientation sessions start at 9:30 AM local time on your start date. The welcome schedule above details the link and location."
            },
            {
                "question": "How do I request software access?",
                "answer": "Log in to the Slack workspace once your email is provisioned and request credentials from the #it-helpdesk channel."
            },
            {
                "question": "When will my equipment arrive?",
                "answer": "Equipment is ordered upon NDA completion. You can track your laptop delivery status in the Equipment section."
            }
        ]
    }
