from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StudentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProgressInput(StudentModel):
    percent: float = Field(ge=0, le=100)
    lastSection: str | None = Field(default=None, max_length=160)


class AttemptInput(StudentModel):
    answer: Any
