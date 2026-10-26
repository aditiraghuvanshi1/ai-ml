"""Students Database CRUD API (FastAPI + SQLite)."""
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response

import ai
import database as db
from schemas import AIAnswer, AIQuestion, Student, StudentCreate, StudentUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()          # creates the table on first run; data persists in students.db
    yield


app = FastAPI(
    title="Students Database CRUD API",
    description="Manage student records with FastAPI and SQLite. Includes an optional local-AI (Ollama) endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)


def _not_found(student_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Student with id {student_id} not found")


def _integrity_error(exc: sqlite3.IntegrityError) -> HTTPException:
    if "UNIQUE" in str(exc).upper():
        return HTTPException(status_code=409, detail="A student with this email already exists")
    return HTTPException(status_code=422, detail="A student must keep at least an email or a phone number")


@app.get("/", tags=["info"])
def root():
    return {"message": "Students CRUD API is running", "docs": "/docs"}


# ---------- CREATE ----------
@app.post("/students", response_model=Student, status_code=201, tags=["students"])
def create_student(student: StudentCreate):
    try:
        return db.create_student(student.model_dump(mode="json"))
    except sqlite3.IntegrityError as exc:
        raise _integrity_error(exc)


# ---------- READ ----------
@app.get("/students", response_model=list[Student], tags=["students"])
def list_students(
    name: Optional[str] = Query(None, description="Partial name match"),
    course: Optional[str] = Query(None, description="Partial course match"),
    born_after: Optional[date] = Query(None, description="Date of birth on or after this date"),
    born_before: Optional[date] = Query(None, description="Date of birth on or before this date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return db.list_students(
        name=name,
        course=course,
        born_after=born_after.isoformat() if born_after else None,
        born_before=born_before.isoformat() if born_before else None,
        limit=limit,
        offset=offset,
    )


@app.get("/students/{student_id}", response_model=Student, tags=["students"])
def get_student(student_id: int):
    student = db.get_student(student_id)
    if student is None:
        raise _not_found(student_id)
    return student


# ---------- UPDATE ----------
@app.put("/students/{student_id}", response_model=Student, tags=["students"])
def replace_student(student_id: int, student: StudentCreate):
    """Full update: every field is replaced (omitted optional fields become empty)."""
    data = student.model_dump(mode="json")
    try:
        updated = db.update_student(student_id, data)
    except sqlite3.IntegrityError as exc:
        raise _integrity_error(exc)
    if updated is None:
        raise _not_found(student_id)
    return updated


@app.patch("/students/{student_id}", response_model=Student, tags=["students"])
def patch_student(student_id: int, changes: StudentUpdate):
    """Partial update: only the fields you send are changed."""
    data = changes.model_dump(mode="json", exclude_unset=True)
    try:
        updated = db.update_student(student_id, data)
    except sqlite3.IntegrityError as exc:
        raise _integrity_error(exc)
    if updated is None:
        raise _not_found(student_id)
    return updated


# ---------- DELETE ----------
@app.delete("/students/{student_id}", status_code=204, tags=["students"])
def delete_student(student_id: int):
    if not db.delete_student(student_id):
        raise _not_found(student_id)
    return Response(status_code=204)


# ---------- OPTIONAL BONUS: local AI with Ollama ----------
@app.post("/ai/ask", response_model=AIAnswer, tags=["ai (optional)"])
def ask_ai(body: AIQuestion):
    """Ask a natural-language question. The backend fetches matching records and gives them
    to the model as context. The model never receives or runs SQL."""
    try:
        return ai.answer_question(body.question)
    except ai.OllamaUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
