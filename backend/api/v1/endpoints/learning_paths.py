import logging
import uuid
import io
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from ..auth import verify_token
from ....core.database import get_db, LearningPathModel

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


LEARNING_PATHS = [
    {
        "id": "master-multiplication",
        "title": "Master Multiplication in 30 Days",
        "description": "Build a strong foundation in multiplication from times tables to multi-digit problems.",
        "subject": "math",
        "icon": "✖️",
        "color": "#00f5ff",
        "estimated_days": 30,
        "milestones": [
            {"id": "m1", "title": "Times Tables 1-5", "description": "Master multiplication tables for 1 through 5", "requirements": {"skill": "multiplication", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Times Tables 6-10", "description": "Master multiplication tables for 6 through 10", "requirements": {"skill": "multiplication", "mastery": 0.45, "lessons": 3}},
            {"id": "m3", "title": "Times Tables 11-12", "description": "Complete all times tables up to 12", "requirements": {"skill": "multiplication", "mastery": 0.55, "lessons": 4}},
            {"id": "m4", "title": "Word Problems", "description": "Solve multiplication word problems", "requirements": {"skill": "multiplication", "mastery": 0.65, "lessons": 5}},
            {"id": "m5", "title": "Multi-Digit Multiplication", "description": "Multiply two-digit numbers confidently", "requirements": {"skill": "multiplication", "mastery": 0.75, "lessons": 7}},
            {"id": "m6", "title": "Multiplication Master", "description": "Achieve full mastery of multiplication", "requirements": {"skill": "multiplication", "mastery": 0.9, "lessons": 10}},
        ],
    },
    {
        "id": "science-explorer",
        "title": "Science Explorer",
        "description": "Journey through the wonders of science from living things to the solar system.",
        "subject": "science",
        "icon": "🔬",
        "color": "#00ff88",
        "estimated_days": 45,
        "milestones": [
            {"id": "m1", "title": "Living Things", "description": "Understand the difference between living and non-living things", "requirements": {"skill": "plants", "mastery": 0.3, "lessons": 1}},
            {"id": "m2", "title": "Plant Life", "description": "Learn about plant parts and how plants grow", "requirements": {"skill": "plants", "mastery": 0.5, "lessons": 3}},
            {"id": "m3", "title": "Animal Kingdom", "description": "Explore different animal groups and habitats", "requirements": {"skill": "animals", "mastery": 0.5, "lessons": 5}},
            {"id": "m4", "title": "Weather Watcher", "description": "Understand weather patterns and the water cycle", "requirements": {"skill": "weather", "mastery": 0.5, "lessons": 7}},
            {"id": "m5", "title": "Matter Expert", "description": "Master states of matter and their properties", "requirements": {"skill": "matter", "mastery": 0.6, "lessons": 9}},
            {"id": "m6", "title": "Space Cadet", "description": "Learn about the solar system and planets", "requirements": {"skill": "ecosystems", "mastery": 0.6, "lessons": 11}},
            {"id": "m7", "title": "Science Champion", "description": "Complete all science topics with high mastery", "requirements": {"skill": "ecosystems", "mastery": 0.8, "lessons": 14}},
        ],
    },
    {
        "id": "reading-champion",
        "title": "Reading Champion",
        "description": "From phonics to comprehension — become a confident and skilled reader.",
        "subject": "reading",
        "icon": "📖",
        "color": "#ff00ff",
        "estimated_days": 60,
        "milestones": [
            {"id": "m1", "title": "Letter Sounds", "description": "Master basic phonics and letter sounds", "requirements": {"skill": "phonics", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Word Builder", "description": "Read and spell simple words fluently", "requirements": {"skill": "phonics", "mastery": 0.5, "lessons": 4}},
            {"id": "m3", "title": "Vocabulary Explorer", "description": "Build a strong vocabulary foundation", "requirements": {"skill": "vocabulary", "mastery": 0.4, "lessons": 6}},
            {"id": "m4", "title": "Story Detective", "description": "Understand main ideas and story details", "requirements": {"skill": "comprehension", "mastery": 0.5, "lessons": 8}},
            {"id": "m5", "title": "Inference Master", "description": "Read between the lines and make predictions", "requirements": {"skill": "inference", "mastery": 0.5, "lessons": 10}},
            {"id": "m6", "title": "Reading Champion", "description": "Achieve reading mastery across all skills", "requirements": {"skill": "comprehension", "mastery": 0.8, "lessons": 14}},
        ],
    },
    {
        "id": "code-adventurer",
        "title": "Code Adventurer",
        "description": "Learn to think like a programmer with fun coding challenges.",
        "subject": "coding",
        "icon": "💻",
        "color": "#8b5cf6",
        "estimated_days": 40,
        "milestones": [
            {"id": "m1", "title": "First Commands", "description": "Write your first sequences of instructions", "requirements": {"skill": "variables", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Loop Hero", "description": "Master repeating instructions with loops", "requirements": {"skill": "loops", "mastery": 0.4, "lessons": 4}},
            {"id": "m3", "title": "Decision Maker", "description": "Use conditionals to make smart choices", "requirements": {"skill": "conditionals", "mastery": 0.4, "lessons": 6}},
            {"id": "m4", "title": "Variable Wizard", "description": "Store and manipulate data with variables", "requirements": {"skill": "variables", "mastery": 0.6, "lessons": 8}},
            {"id": "m5", "title": "Function Builder", "description": "Create reusable code with functions", "requirements": {"skill": "functions", "mastery": 0.5, "lessons": 10}},
            {"id": "m6", "title": "Algorithm Ace", "description": "Solve complex problems with algorithms", "requirements": {"skill": "algorithms", "mastery": 0.6, "lessons": 12}},
            {"id": "m7", "title": "Code Adventurer", "description": "Complete all coding challenges", "requirements": {"skill": "algorithms", "mastery": 0.8, "lessons": 15}},
        ],
    },
    {
        "id": "fraction-fundamentals",
        "title": "Fraction Fundamentals",
        "description": "Master fractions from basic concepts to operations and real-world applications.",
        "subject": "math",
        "icon": "🥧",
        "color": "#00f5ff",
        "estimated_days": 25,
        "milestones": [
            {"id": "m1", "title": "What are Fractions?", "description": "Understand parts of a whole", "requirements": {"skill": "fractions", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Comparing Fractions", "description": "Compare and order fractions", "requirements": {"skill": "fractions", "mastery": 0.45, "lessons": 4}},
            {"id": "m3", "title": "Adding Fractions", "description": "Add fractions with same denominators", "requirements": {"skill": "fractions", "mastery": 0.55, "lessons": 6}},
            {"id": "m4", "title": "Subtracting Fractions", "description": "Subtract fractions confidently", "requirements": {"skill": "fractions", "mastery": 0.65, "lessons": 8}},
            {"id": "m5", "title": "Fraction Master", "description": "Master all fraction operations", "requirements": {"skill": "fractions", "mastery": 0.85, "lessons": 10}},
        ],
    },
    {
        "id": "ecosystem-expert",
        "title": "Ecosystem Expert",
        "description": "Dive deep into ecosystems, food chains, and how living things interact.",
        "subject": "science",
        "icon": "🌍",
        "color": "#00ff88",
        "estimated_days": 30,
        "milestones": [
            {"id": "m1", "title": "Habitats", "description": "Learn about different animal habitats", "requirements": {"skill": "ecosystems", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Food Chains", "description": "Understand producers and consumers", "requirements": {"skill": "ecosystems", "mastery": 0.45, "lessons": 4}},
            {"id": "m3", "title": "Adaptation", "description": "Learn how animals adapt to environments", "requirements": {"skill": "animals", "mastery": 0.5, "lessons": 6}},
            {"id": "m4", "title": "Water Cycle", "description": "Master the water cycle and its importance", "requirements": {"skill": "weather", "mastery": 0.5, "lessons": 8}},
            {"id": "m5", "title": "Ecosystem Guardian", "description": "Understand conservation and resources", "requirements": {"skill": "ecosystems", "mastery": 0.75, "lessons": 10}},
        ],
    },
    {
        "id": "geometry-genius",
        "title": "Geometry Genius",
        "description": "Explore shapes, measurements, area, and volume in this geometry adventure.",
        "subject": "math",
        "icon": "📐",
        "color": "#00f5ff",
        "estimated_days": 35,
        "milestones": [
            {"id": "m1", "title": "Basic Shapes", "description": "Identify and name 2D shapes", "requirements": {"skill": "geometry", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Measuring Up", "description": "Learn to measure length and width", "requirements": {"skill": "measurement", "mastery": 0.4, "lessons": 4}},
            {"id": "m3", "title": "Perimeter Pro", "description": "Calculate perimeters of shapes", "requirements": {"skill": "geometry", "mastery": 0.5, "lessons": 6}},
            {"id": "m4", "title": "Area Expert", "description": "Calculate area of rectangles and triangles", "requirements": {"skill": "geometry", "mastery": 0.65, "lessons": 8}},
            {"id": "m5", "title": "3D Explorer", "description": "Understand 3D shapes and volume", "requirements": {"skill": "geometry", "mastery": 0.75, "lessons": 10}},
            {"id": "m6", "title": "Geometry Genius", "description": "Master all geometry concepts", "requirements": {"skill": "geometry", "mastery": 0.9, "lessons": 12}},
        ],
    },
    {
        "id": "word-wizard",
        "title": "Word Wizard",
        "description": "Build an amazing vocabulary and become a master of words.",
        "subject": "reading",
        "icon": "🧙",
        "color": "#ff00ff",
        "estimated_days": 30,
        "milestones": [
            {"id": "m1", "title": "Sight Words", "description": "Master common sight words", "requirements": {"skill": "vocabulary", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Context Clues", "description": "Use context to understand new words", "requirements": {"skill": "vocabulary", "mastery": 0.45, "lessons": 4}},
            {"id": "m3", "title": "Word Families", "description": "Learn word roots and families", "requirements": {"skill": "vocabulary", "mastery": 0.55, "lessons": 6}},
            {"id": "m4", "title": "Figurative Language", "description": "Understand similes, metaphors, and idioms", "requirements": {"skill": "vocabulary", "mastery": 0.7, "lessons": 8}},
            {"id": "m5", "title": "Word Wizard", "description": "Achieve vocabulary mastery", "requirements": {"skill": "vocabulary", "mastery": 0.85, "lessons": 10}},
        ],
    },
    {
        "id": "division-discovery",
        "title": "Division Discovery",
        "description": "Learn division from sharing equally to long division and remainders.",
        "subject": "math",
        "icon": "➗",
        "color": "#00f5ff",
        "estimated_days": 25,
        "milestones": [
            {"id": "m1", "title": "Equal Sharing", "description": "Understand division as sharing equally", "requirements": {"skill": "division", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Division Facts", "description": "Master basic division facts", "requirements": {"skill": "division", "mastery": 0.45, "lessons": 4}},
            {"id": "m3", "title": "Remainders", "description": "Handle division with remainders", "requirements": {"skill": "division", "mastery": 0.55, "lessons": 6}},
            {"id": "m4", "title": "Long Division", "description": "Master long division technique", "requirements": {"skill": "division", "mastery": 0.7, "lessons": 8}},
            {"id": "m5", "title": "Division Champion", "description": "Achieve full division mastery", "requirements": {"skill": "division", "mastery": 0.85, "lessons": 10}},
        ],
    },
    {
        "id": "forces-and-energy",
        "title": "Forces & Energy Explorer",
        "description": "Discover how forces, motion, and energy shape our world.",
        "subject": "science",
        "icon": "⚡",
        "color": "#00ff88",
        "estimated_days": 35,
        "milestones": [
            {"id": "m1", "title": "Push and Pull", "description": "Understand basic forces and motion", "requirements": {"skill": "forces", "mastery": 0.3, "lessons": 2}},
            {"id": "m2", "title": "Simple Machines", "description": "Learn about levers, pulleys, and more", "requirements": {"skill": "forces", "mastery": 0.45, "lessons": 4}},
            {"id": "m3", "title": "Energy Types", "description": "Identify different forms of energy", "requirements": {"skill": "energy", "mastery": 0.45, "lessons": 6}},
            {"id": "m4", "title": "Electricity Basics", "description": "Understand circuits and conductors", "requirements": {"skill": "energy", "mastery": 0.6, "lessons": 8}},
            {"id": "m5", "title": "Magnetism", "description": "Explore magnets and magnetic fields", "requirements": {"skill": "forces", "mastery": 0.65, "lessons": 10}},
            {"id": "m6", "title": "Energy Master", "description": "Master all force and energy concepts", "requirements": {"skill": "energy", "mastery": 0.8, "lessons": 12}},
        ],
    },
]

def _get_path(path_id: str):
    for p in LEARNING_PATHS:
        if p["id"] == path_id:
            return p
    return None


async def _get_enrollment_db(db, user_id: str, path_id: str):
    result = await db.execute(
        select(LearningPathModel).where(
            LearningPathModel.user_id == user_id,
            LearningPathModel.path_id == path_id,
        )
    )
    return result.scalar_one_or_none()


def _enrollment_to_dict(enrollment):
    if not enrollment:
        return None
    return {
        "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
        "completed_milestones": enrollment.completed_milestones or [],
        "completed": enrollment.completed or False,
        "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None,
        "certificate_id": enrollment.certificate_id,
    }


def _compute_milestone_progress(enrollment_dict, path):
    completed = enrollment_dict.get("completed_milestones", []) if enrollment_dict else []
    milestones = path["milestones"]
    total = len(milestones)
    done = len([m for m in milestones if m["id"] in completed])
    return done, total


@router.get("")
async def list_learning_paths(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    user_enrollments = {}
    result_rows = await db.execute(
        select(LearningPathModel).where(LearningPathModel.user_id == user_id)
    )
    for row in result_rows.scalars().all():
        user_enrollments[row.path_id] = _enrollment_to_dict(row)

    result = []
    for path in LEARNING_PATHS:
        enrollment = user_enrollments.get(path["id"])
        enrolled = enrollment is not None
        completed = enrollment.get("completed", False) if enrollment else False
        done, total = _compute_milestone_progress(enrollment, path) if enrollment else (0, len(path["milestones"]))
        progress_pct = round((done / total) * 100) if total > 0 else 0

        result.append({
            "id": path["id"],
            "title": path["title"],
            "description": path["description"],
            "subject": path["subject"],
            "icon": path["icon"],
            "color": path["color"],
            "estimated_days": path["estimated_days"],
            "milestone_count": total,
            "enrolled": enrolled,
            "completed": completed,
            "milestones_done": done,
            "progress_pct": progress_pct,
        })
    return {"paths": result}


@router.get("/{path_id}")
async def get_learning_path(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    path = _get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enrollment_row = await _get_enrollment_db(db, user_id, path_id)
    enrollment = _enrollment_to_dict(enrollment_row)
    enrolled = enrollment is not None
    completed = enrollment.get("completed", False) if enrollment else False
    completed_milestones = enrollment.get("completed_milestones", []) if enrollment else []
    certificate_id = enrollment.get("certificate_id") if enrollment else None

    milestones_detail = []
    for m in path["milestones"]:
        milestones_detail.append({
            **m,
            "completed": m["id"] in completed_milestones,
        })

    done, total = _compute_milestone_progress(enrollment, path) if enrollment else (0, len(path["milestones"]))

    return {
        **path,
        "enrolled": enrolled,
        "completed": completed,
        "milestones_done": done,
        "progress_pct": round((done / total) * 100) if total > 0 else 0,
        "milestones": milestones_detail,
        "certificate_id": certificate_id,
    }


@router.post("/{path_id}/enroll")
async def enroll_in_path(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    path = _get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    existing = await _get_enrollment_db(db, user_id, path_id)
    if existing:
        return {"message": "Already enrolled", "path_id": path_id}

    new_enrollment = LearningPathModel(
        user_id=user_id,
        path_id=path_id,
        completed_milestones=[],
        completed=False,
    )
    db.add(new_enrollment)
    await db.commit()

    return {"message": "Successfully enrolled", "path_id": path_id}


@router.post("/{path_id}/milestone/{milestone_id}/complete")
async def complete_milestone(
    path_id: str,
    milestone_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    path = _get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enrollment = await _get_enrollment_db(db, user_id, path_id)
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this path")

    milestone_ids = [m["id"] for m in path["milestones"]]
    if milestone_id not in milestone_ids:
        raise HTTPException(status_code=404, detail="Milestone not found")

    current_milestones = list(enrollment.completed_milestones or [])
    if milestone_id not in current_milestones:
        current_milestones.append(milestone_id)
        enrollment.completed_milestones = current_milestones

    if set(current_milestones) >= set(milestone_ids):
        enrollment.completed = True
        enrollment.completed_at = datetime.now(timezone.utc)
        enrollment.certificate_id = str(uuid.uuid4())[:12].upper()

    await db.commit()
    await db.refresh(enrollment)

    done = len([m for m in path["milestones"] if m["id"] in current_milestones])
    total = len(path["milestones"])

    return {
        "message": "Milestone completed",
        "milestone_id": milestone_id,
        "milestones_done": done,
        "total_milestones": total,
        "path_completed": enrollment.completed,
        "certificate_id": enrollment.certificate_id,
    }


@router.get("/{path_id}/certificate")
async def get_certificate(
    path_id: str,
    user_id: str = Depends(get_current_user_id),
    student_name: str = Query(default="Star Student"),
    db=Depends(get_db),
):
    path = _get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enrollment = await _get_enrollment_db(db, user_id, path_id)
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this path")

    if not enrollment.completed:
        raise HTTPException(status_code=400, detail="Path not yet completed")

    certificate_id = enrollment.certificate_id or "CERT-0000"
    completed_at = enrollment.completed_at.isoformat() if enrollment.completed_at else datetime.now(timezone.utc).isoformat()

    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    w = 297
    h = 210

    pdf.set_fill_color(10, 10, 42)
    pdf.rect(0, 0, w, h, "F")

    pdf.set_draw_color(0, 200, 255)
    pdf.set_line_width(3)
    pdf.rect(10, 10, w - 20, h - 20)

    pdf.set_draw_color(139, 92, 246)
    pdf.set_line_width(1.5)
    pdf.rect(15, 15, w - 30, h - 30)

    pdf.set_draw_color(0, 200, 255)
    pdf.set_line_width(0.5)
    for i in range(0, w, 15):
        pdf.line(i, 10, i, 13)
        pdf.line(i, h - 13, i, h - 10)
    for i in range(0, h, 15):
        pdf.line(10, i, 13, i)
        pdf.line(w - 13, i, w - 10, i)

    pdf.set_text_color(0, 200, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(0, 25)
    pdf.cell(w, 10, "NEXTGEN AI TUTOR", align="C")

    pdf.set_text_color(220, 220, 240)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(0, 37)
    pdf.cell(w, 8, "CERTIFICATE OF ACHIEVEMENT", align="C")

    pdf.set_text_color(200, 200, 220)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_xy(0, 55)
    pdf.cell(w, 10, "This certificate is proudly awarded to", align="C")

    pdf.set_text_color(0, 245, 255)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_xy(0, 68)
    pdf.cell(w, 16, student_name, align="C")

    pdf.set_draw_color(0, 200, 255)
    pdf.set_line_width(0.5)
    pdf.line(w / 2 - 60, 86, w / 2 + 60, 86)

    pdf.set_text_color(200, 200, 220)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_xy(0, 92)
    pdf.cell(w, 10, "for successfully completing the learning path", align="C")

    pdf.set_text_color(139, 92, 246)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_xy(0, 106)
    pdf.cell(w, 14, path["title"], align="C")

    milestone_count = len(path["milestones"])
    pdf.set_text_color(180, 180, 200)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(0, 124)
    pdf.cell(w, 8, f"Completing all {milestone_count} milestones in {path['subject'].title()}", align="C")

    try:
        date_str = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).strftime("%B %d, %Y")
    except Exception:
        date_str = completed_at[:10]

    pdf.set_text_color(160, 160, 180)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(30, 150)
    pdf.cell(100, 8, f"Date: {date_str}", align="C")

    pdf.set_xy(w - 130, 150)
    pdf.cell(100, 8, f"Certificate ID: {certificate_id}", align="C")

    pdf.set_draw_color(100, 100, 140)
    pdf.set_line_width(0.3)
    pdf.line(40, 160, 130, 160)
    pdf.line(w - 130, 160, w - 40, 160)

    pdf.set_text_color(120, 120, 150)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(0, h - 30)
    pdf.cell(w, 6, "Powered by NextGen AI Tutor - Personalized Learning Platform", align="C")

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    filename = f"certificate_{path_id}_{certificate_id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["router"]
