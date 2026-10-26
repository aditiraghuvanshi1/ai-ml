"""Pydantic models: request validation and response shapes."""
from datetime import date
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, StringConstraints, model_validator


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("date cannot be in the future")
    return value


def _lowercase(value: str) -> str:
    return value.lower()


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=254,
                      pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    AfterValidator(_lowercase),
]
Phone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9][0-9 \-]{6,18}$"),
]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
BirthDate = Annotated[date, AfterValidator(_not_in_future)]
EnrollDate = Annotated[date, AfterValidator(_not_in_future)]


class StudentCreate(BaseModel):
    """Body for POST (create) and PUT (full replace)."""
    name: Name
    date_of_birth: BirthDate
    email: Optional[Email] = None
    phone: Optional[Phone] = None
    course: Optional[Text] = None
    address: Optional[Text] = None
    enrollment_date: Optional[EnrollDate] = None

    @model_validator(mode="after")
    def require_contact(self):
        if not self.email and not self.phone:
            raise ValueError("provide at least one contact: email or phone")
        return self


class StudentUpdate(BaseModel):
    """Body for PATCH. Send only the fields you want to change."""
    name: Optional[Name] = None
    date_of_birth: Optional[BirthDate] = None
    email: Optional[Email] = None
    phone: Optional[Phone] = None
    course: Optional[Text] = None
    address: Optional[Text] = None
    enrollment_date: Optional[EnrollDate] = None

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("send at least one field to update")
        for required in ("name", "date_of_birth"):
            if required in self.model_fields_set and getattr(self, required) is None:
                raise ValueError(f"{required} cannot be null")
        return self


class Student(BaseModel):
    id: int
    name: str
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None
    created_at: str


class AIQuestion(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class AIAnswer(BaseModel):
    question: str
    answer: str
    records_used: int
    model: str
