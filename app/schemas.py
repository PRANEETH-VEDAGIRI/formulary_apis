"""Pydantic request / response schemas — full CRUD."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CreateRequest(BaseModel):
    """Single row or list of rows to insert."""
    data: dict[str, Any] | list[dict[str, Any]] = Field(
        ...,
        description="Row(s) to create. Provide only user-input columns; IDs/timestamps are auto-generated.",
    )


class UpdateRequest(BaseModel):
    """Partial or full update payload for a single row."""
    data: dict[str, Any] = Field(
        ...,
        description="Fields to update. For PATCH, only provided fields are changed. For PUT, all user columns are replaced.",
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


class RowResponse(BaseModel):
    """Response for a single-row fetch (GET by ID)."""
    success: bool
    table: str
    data: dict[str, Any]


class ListResponse(BaseModel):
    """Paginated list response for GET all."""
    success: bool
    table: str
    total: int
    page: int
    page_size: int
    data: list[dict[str, Any]]


class UpdateResponse(BaseModel):
    """Response for PUT / PATCH operations."""

    model_config = ConfigDict(extra="allow")

    success: bool
    table: str
    updated: int
    message: str


class DeleteResponse(BaseModel):
    """Response for DELETE operations."""
    success: bool
    table: str
    deleted: int
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    detail: str


class TableInfo(BaseModel):
    slug: str
    table: str
    user_columns: list[str]
