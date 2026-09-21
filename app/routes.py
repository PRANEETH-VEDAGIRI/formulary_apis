"""
Routes — full CRUD for all 12 formulary tables (JWT-protected).

GET    /api/v1/formulary/tables          — list slugs + user columns
POST   /api/v1/formulary/{slug}          — create one or many rows
GET    /api/v1/formulary/{slug}          — list rows (paginated, filterable)
GET    /api/v1/formulary/{slug}/{id}     — get single row by ID
PUT    /api/v1/formulary/{slug}/{id}     — full replace (all user cols)
PATCH  /api/v1/formulary/{slug}/{id}     — partial update (only sent fields)
DELETE /api/v1/formulary/{slug}/{id}     — delete row by ID
POST   /api/v1/auth/token                — generate JWT token
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from app.schemas import (
    CreateRequest, CreateResponse,
    UpdateRequest, UpdateResponse,
    RowResponse, ListResponse,
    DeleteResponse, TableInfo,
)
from app.table_config import SLUG_MAP, get_table_config, get_all_configs, get_id_key
from app.auth import create_token, require_auth
from app.validator import validate_batch, validate_update
from app import crud
from config import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX

router = APIRouter(prefix="/api/v1/formulary", tags=["formulary"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _require_cfg(table_slug: str):
    cfg = get_table_config(table_slug)
    if cfg is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown table '{table_slug}'. Available: {', '.join(sorted(SLUG_MAP.keys()))}",
        )
    return cfg


def _conflict_or_500(e: Exception) -> HTTPException:
    """Map DB data-rule errors to clean codes (no DB internals leaked):
    not-null → 400, FK RESTRICT / trigger blocks / unique → 409, rest → 500."""
    msg = str(e).lower()
    if "violates not-null" in msg or "null value in column" in msg or "not-null constraint" in msg:
        return HTTPException(status_code=400, detail="Invalid data: a required field is missing or null")
    if any(k in msg for k in (
        "foreign key", "violates foreign", "violates unique", "unique constraint",
        "restrict", "prevent_pbp_delete", "already exists", "duplicate",
    )):
        return HTTPException(status_code=409, detail="Conflict: record is referenced by other data or violates a uniqueness rule")
    return HTTPException(status_code=500, detail="Internal server error")


# ── Token endpoint ──────────────────────────────────────────────────
class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@auth_router.post("/token", response_model=TokenResponse)
def generate_token(req: TokenRequest):
    """Mint a JWT token — ONLY for the single server-side credential pair
    (API_USERNAME / API_PASSWORD from environment). Everything else → 401.
    If the pair is not configured, issuance is disabled (fail closed)."""
    import hmac
    from config import API_USERNAME, API_PASSWORD

    if not API_USERNAME or not API_PASSWORD:
        raise HTTPException(status_code=500, detail="Token issuance is not configured on this server")
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    user_ok = hmac.compare_digest(req.username, API_USERNAME)
    pass_ok = hmac.compare_digest(req.password, API_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token({"sub": API_USERNAME, "role": "admin"})
    return TokenResponse(access_token=token)


# ── List available tables (must come before /{slug} routes) ─────────
@router.get("/tables", response_model=list[TableInfo])
def list_tables(user: dict = Depends(require_auth)):
    """List all available table slugs and the columns the user must provide."""
    configs = get_all_configs()
    return [
        TableInfo(
            slug=slug,
            table=f"{cfg['schema']}.{cfg['table']}",
            user_columns=cfg["user_columns"],
            required_columns=cfg.get("required_columns", []),
            pk_column=cfg.get("pk_column", "id"),
        )
        for slug, cfg in sorted(configs.items())
    ]


# ── CREATE ──────────────────────────────────────────────────────────
@router.post("/{table_slug}", response_model=CreateResponse)
def create_record(
    table_slug: str,
    req: CreateRequest,
    user: dict = Depends(require_auth),
):
    """Create one or more rows. DB generates the ID; response returns the
    DB-created PK under a table-specific key (e.g. payer_id) for FK chaining."""
    _require_cfg(table_slug)

    payload = req.data if isinstance(req.data, list) else [req.data]

    errors = validate_batch(table_slug, payload)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    try:
        ids = crud.create_rows(table_slug, payload)
        id_key = get_id_key(table_slug)
        id_value = ids[0] if len(ids) == 1 else ids
        return CreateResponse(
            success=True,
            table=table_slug,
            inserted=len(ids),
            message=f"{len(ids)} row(s) created",
            **{id_key: id_value},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise _conflict_or_500(e)


# ── READ — list (paginated + filterable) ────────────────────────────
@router.get("/{table_slug}", response_model=ListResponse)
def list_records(
    table_slug: str,
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX, description="Rows per page"),
    user: dict = Depends(require_auth),
):
    """List rows with pagination. Any extra query param filters by exact match,
    e.g. ?status=active&type=Commercial (unknown columns are ignored)."""
    _require_cfg(table_slug)

    filters = {
        k: v for k, v in request.query_params.items()
        if k not in ("page", "page_size")
    } or None

    try:
        rows, total = crud.get_rows(table_slug, filters=filters, page=page, page_size=page_size)
        return ListResponse(
            success=True,
            table=table_slug,
            total=total,
            page=page,
            page_size=min(page_size, PAGE_SIZE_MAX),
            data=rows,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise _conflict_or_500(e)


# ── READ — single ───────────────────────────────────────────────────
@router.get("/{table_slug}/{row_id}", response_model=RowResponse)
def get_record(
    table_slug: str,
    row_id: str,
    user: dict = Depends(require_auth),
):
    """Fetch a single row by its ID."""
    _require_cfg(table_slug)

    try:
        row = crud.get_row_by_id(table_slug, row_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{table_slug}'")
        return RowResponse(success=True, table=table_slug, data=row)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise _conflict_or_500(e)


# ── UPDATE — full (PUT) ─────────────────────────────────────────────
@router.put("/{table_slug}/{row_id}", response_model=UpdateResponse)
def replace_record(
    table_slug: str,
    row_id: str,
    req: UpdateRequest,
    user: dict = Depends(require_auth),
):
    """Full update — replaces ALL user columns. PK is immutable (DB owns it)."""
    _require_cfg(table_slug)

    errors = validate_update(table_slug, req.data, partial=False)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    try:
        updated_id = crud.update_row(table_slug, row_id, req.data, partial=False)
        if updated_id is None:
            raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{table_slug}'")
        id_key = get_id_key(table_slug)
        return UpdateResponse(
            success=True,
            table=table_slug,
            updated=1,
            message="1 row(s) updated",
            **{id_key: updated_id},
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise _conflict_or_500(e)


# ── UPDATE — partial (PATCH) ────────────────────────────────────────
@router.patch("/{table_slug}/{row_id}", response_model=UpdateResponse)
def update_record(
    table_slug: str,
    row_id: str,
    req: UpdateRequest,
    user: dict = Depends(require_auth),
):
    """Partial update — only the fields you send are changed."""
    _require_cfg(table_slug)

    errors = validate_update(table_slug, req.data, partial=True)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    try:
        updated_id = crud.update_row(table_slug, row_id, req.data, partial=True)
        if updated_id is None:
            raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{table_slug}'")
        id_key = get_id_key(table_slug)
        return UpdateResponse(
            success=True,
            table=table_slug,
            updated=1,
            message="1 row(s) updated",
            **{id_key: updated_id},
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise _conflict_or_500(e)


# ── DELETE ──────────────────────────────────────────────────────────
@router.delete("/{table_slug}/{row_id}", response_model=DeleteResponse)
def delete_record(
    table_slug: str,
    row_id: str,
    user: dict = Depends(require_auth),
):
    """Delete a row by ID. Returns 409 if other records reference it (FK RESTRICT)
    or a DB trigger blocks the delete — nothing is partially removed."""
    _require_cfg(table_slug)

    try:
        deleted = crud.delete_row(table_slug, row_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{table_slug}'")
        return DeleteResponse(
            success=True,
            table=table_slug,
            deleted=1,
            message="1 row(s) deleted",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise _conflict_or_500(e)
