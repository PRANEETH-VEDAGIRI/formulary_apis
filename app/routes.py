"""
Routes — POST /api/v1/formulary/{table_slug}  (CREATE only)
GET /api/v1/formulary/tables  — list slugs + user columns
POST /api/v1/auth/token        — generate JWT token
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.schemas import CreateRequest, CreateResponse, TableInfo
from app.table_config import SLUG_MAP, get_table_config, get_all_configs, get_id_key
from app.auth import create_token, require_auth
from app.validator import validate_batch
from app import crud

router = APIRouter(prefix="/api/v1/formulary", tags=["formulary"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Token endpoint ──────────────────────────────────────────────────
class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@auth_router.post("/token", response_model=TokenResponse)
def generate_token(req: TokenRequest):
    """Generate a JWT token. In production, validate against your identity provider.
    For now, accepts any non-empty username/password pair."""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    token = create_token({"sub": req.username, "role": "admin"})
    return TokenResponse(access_token=token)


# ── Protected formulary routes ──────────────────────────────────────
@router.post("/{table_slug}", response_model=CreateResponse)
def create_record(
    table_slug: str,
    req: CreateRequest,
    user: dict = Depends(require_auth),
):
    """Create one or more rows. Returns the created PK under a
    table-specific key (e.g. payer_id, brand_id) for FK chaining."""
    cfg = get_table_config(table_slug)
    if cfg is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown table '{table_slug}'. Available: {', '.join(sorted(SLUG_MAP.keys()))}",
        )

    payload = req.data if isinstance(req.data, list) else [req.data]

    # Validate against DB schema constraints
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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tables", response_model=list[TableInfo])
def list_tables(user: dict = Depends(require_auth)):
    """List all available table slugs and the columns the user must provide."""
    configs = get_all_configs()
    return [
        TableInfo(
            slug=slug,
            table=f"{cfg['schema']}.{cfg['table']}",
            user_columns=cfg["user_columns"],
        )
        for slug, cfg in sorted(configs.items())
    ]
