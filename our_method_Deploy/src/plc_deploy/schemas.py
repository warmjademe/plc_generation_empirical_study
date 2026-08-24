from __future__ import annotations

import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _normalize_requirement(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("requirement must not be blank")
    if any(
        unicodedata.category(character) in {"Cc", "Cf"}
        and character not in "\n\r\t"
        for character in normalized
    ):
        raise ValueError("requirement contains unsupported control characters or invisible characters")
    return normalized


class JobCreate(BaseModel):
    requirement: str = Field(min_length=1, max_length=20000)
    vendor: str = "delta"
    plc_model: str = "DVP48ES300R"
    llm_model: str = "deepseek-v4-pro"
    output_language: Literal["st", "ld"] = "st"
    # Keep non-browser API clients backward compatible; the production Web UI
    # explicitly requests downloadable_project as its default selection.
    delivery_mode: Literal["downloadable_project", "function_unit"] = "function_unit"
    max_candidates: int = Field(default=20, ge=1, le=20)

    @field_validator("requirement")
    @classmethod
    def normalize_requirement(cls, value: str) -> str:
        return _normalize_requirement(value)


class ContractDecision(BaseModel):
    approve: Literal[True]
    engineering_config: dict | None = None


class RequirementCheck(BaseModel):
    requirement: str = Field(min_length=1, max_length=20000)

    @field_validator("requirement")
    @classmethod
    def normalize_requirement(cls, value: str) -> str:
        return _normalize_requirement(value)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class JobView(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: str
    request: dict
    contract: dict | None = None
    result: dict | None = None
    final_program: str | None = None
    last_error: str | None = None
    cancel_requested: bool = False
    cancel_reason: str | None = None
    archived_at: str | None = None
