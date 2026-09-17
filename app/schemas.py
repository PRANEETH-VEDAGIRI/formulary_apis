"""Pydantic request / response schemas — CREATE only."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class CreateRequest(BaseModel):
    """Single row or list of rows to insert."""
    data: dict[str, Any] | list[dict[str, Any]] = Field(
        ...,
        description="Row(s) to create. Provide only user-input columns; IDs/timestamps are auto-generated.",
    )


class CreateResponse(BaseModel):
    success: bool
    table: str
    inserted: int
    ids: list[str] = Field(
        default_factory=list,
        description="Auto-generated IDs of created rows. Use these for FK references in child tables.",
    )
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    detail: str


class TableInfo(BaseModel):
    slug: str
    table: str
    user_columns: list[str]
