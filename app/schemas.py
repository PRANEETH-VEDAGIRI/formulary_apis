"""Pydantic request / response schemas — CREATE only."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CreateRequest(BaseModel):
    """Single row or list of rows to insert."""
    data: dict[str, Any] | list[dict[str, Any]] = Field(
        ...,
        description="Row(s) to create. Provide only user-input columns; IDs/timestamps are auto-generated.",
    )


class CreateResponse(BaseModel):
    """Response for a create call. Includes the created PK under a
    table-specific key (e.g. payer_id, plan_id, brand_id) so callers
    know exactly which ID to use for FK chaining."""

    model_config = ConfigDict(extra="allow")

    success: bool
    table: str
    inserted: int
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    detail: str


class TableInfo(BaseModel):
    slug: str
    table: str
    user_columns: list[str]
