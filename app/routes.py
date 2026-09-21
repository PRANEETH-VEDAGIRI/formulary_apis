"""
Routes — one explicit JWT-protected endpoint set per table (no slug typing).

Per table <slug> (e.g. payers, plans, drug-formulary):
  POST   /api/v1/formulary/<slug>            — create one row or a batch
  GET    /api/v1/formulary/<slug>/{row_id}   — get one row by ID
  PUT    /api/v1/formulary/<slug>/{row_id}   — full replace (all user cols)
  PATCH  /api/v1/formulary/<slug>/{row_id}   — partial update (sent fields only)
  DELETE /api/v1/formulary/<slug>/{row_id}   — delete row by ID

Plus:
  GET    /api/v1/formulary/tables  — slugs, columns, required columns, PKs
  POST   /api/v1/auth/token        — mint JWT (single server credential only)

Every request body is pre-filled in Swagger with ALL input columns and sample
values — the user only edits values and executes. Missing REQUIRED columns
fail with 422 before anything touches the DB.
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from app.schemas import (
    CreateResponse, UpdateResponse,
    RowResponse, ListResponse,
    DeleteResponse, TableInfo,
)
from app.table_config import get_all_configs, get_id_key
from app.auth import create_token, require_auth
from app.validator import validate_batch, validate_update
from app import crud

router = APIRouter(prefix="/api/v1/formulary", tags=["formulary"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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


# ── Tables meta ─────────────────────────────────────────────────────
@router.get("/tables", response_model=list[TableInfo])
def list_tables(user: dict = Depends(require_auth)):
    """Reference: every table with its input columns, REQUIRED columns, and PK."""
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


# ── Per-table endpoints (registered at startup — see register_table_routes) ──
def register_table_routes(app) -> None:
    """Create 5 explicit endpoints per table from the live DB schema.

    Called once at startup (after pool init). Each endpoint gets its own
    Swagger section, its own pre-filled request body (ALL columns + samples),
    and returns the created/updated PK under the table's named key
    (payer_id, plan_id, …) for FK chaining.

    Routes are added directly to the FastAPI ``app`` (not the shared router)
    so they appear even though ``app.include_router(router)`` was called earlier.
    """
    from app.table_models import build_table_specs

    for spec in build_table_specs():
        slug = spec["slug"]
        tag = spec["label"]
        id_key = spec["id_key"]
        id_desc = f"{id_key} — UUID from this table's POST response. DB-owned, never sent in bodies."
        _register_one_table(app, slug, tag, id_key, id_desc, spec)


def _register_one_table(app, slug: str, tag: str, id_key: str, id_desc: str, spec: dict) -> None:
    BodyType = spec["BodyType"]
    PatchModel = spec["PatchModel"]
    CreateModel = spec["CreateModel"]

    # ── CREATE (single row or batch) ──
    def create_row(payload: BodyType, user: dict = Depends(require_auth)):
        rows = payload if isinstance(payload, list) else [payload]
        dicts = [r.model_dump(exclude_unset=True) for r in rows]
        errors = validate_batch(slug, dicts)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        try:
            ids = crud.create_rows(slug, dicts)
            id_value = ids[0] if len(ids) == 1 else ids
            return CreateResponse(
                success=True, table=slug, inserted=len(ids),
                message=f"{len(ids)} row(s) created", **{id_key: id_value},
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise _conflict_or_500(e)

    create_row.__name__ = f"create_{spec['func']}"

    # ── READ one ──
    def get_row(row_id: str = Path(..., description=id_desc), user: dict = Depends(require_auth)):
        try:
            row = crud.get_row_by_id(slug, row_id)
            if row is None:
                raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{slug}'")
            return RowResponse(success=True, table=slug, data=row)
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise _conflict_or_500(e)

    get_row.__name__ = f"get_{spec['func']}"

    # ── UPDATE full (PUT) ──
    def replace_row(payload: CreateModel, row_id: str = Path(..., description=id_desc),
                    user: dict = Depends(require_auth)):
        data = payload.model_dump(exclude_unset=True)
        errors = validate_update(slug, data, partial=False)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        try:
            updated = crud.update_row(slug, row_id, data, partial=False)
            if updated is None:
                raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{slug}'")
            return UpdateResponse(success=True, table=slug, updated=1,
                                  message="1 row(s) updated", **{id_key: updated})
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise _conflict_or_500(e)

    replace_row.__name__ = f"replace_{spec['func']}"

    # ── UPDATE partial (PATCH) ──
    def patch_row(payload: PatchModel, row_id: str = Path(..., description=id_desc),
                  user: dict = Depends(require_auth)):
        data = payload.model_dump(exclude_unset=True)
        errors = validate_update(slug, data, partial=True)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        try:
            updated = crud.update_row(slug, row_id, data, partial=True)
            if updated is None:
                raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{slug}'")
            return UpdateResponse(success=True, table=slug, updated=1,
                                  message="1 row(s) updated", **{id_key: updated})
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise _conflict_or_500(e)

    patch_row.__name__ = f"patch_{spec['func']}"

    # ── DELETE ──
    def delete_row(row_id: str = Path(..., description=id_desc), user: dict = Depends(require_auth)):
        try:
            if not crud.delete_row(slug, row_id):
                raise HTTPException(status_code=404, detail=f"Record '{row_id}' not found in '{slug}'")
            return DeleteResponse(success=True, table=slug, deleted=1, message="1 row(s) deleted")
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise _conflict_or_500(e)

    delete_row.__name__ = f"delete_{spec['func']}"

    base = f"/api/v1/formulary/{slug}"
    item = f"/api/v1/formulary/{slug}/{{row_id}}"
    app.add_api_route(base, create_row, methods=["POST"], response_model=CreateResponse,
                      tags=[tag], summary=f"Create {tag}", operation_id=f"create_{spec['func']}")
    app.add_api_route(item, get_row, methods=["GET"], response_model=RowResponse,
                      tags=[tag], summary=f"Get {tag} by ID", operation_id=f"get_{spec['func']}")
    app.add_api_route(item, replace_row, methods=["PUT"], response_model=UpdateResponse,
                      tags=[tag], summary=f"Replace {tag} (full update)", operation_id=f"replace_{spec['func']}")
    app.add_api_route(item, patch_row, methods=["PATCH"], response_model=UpdateResponse,
                      tags=[tag], summary=f"Update {tag} (partial)", operation_id=f"patch_{spec['func']}")
    app.add_api_route(item, delete_row, methods=["DELETE"], response_model=DeleteResponse,
                      tags=[tag], summary=f"Delete {tag}", operation_id=f"delete_{spec['func']}")
