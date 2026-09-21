"""
Routes — POST /api/v1/formulary/{table_slug}  (CREATE only)
GET /api/v1/formulary/tables  — list slugs + user columns
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.schemas import CreateRequest, CreateResponse, TableInfo
from app.table_config import SLUG_MAP, get_table_config, get_all_configs, get_id_key
from app import crud

router = APIRouter(prefix="/api/v1/formulary", tags=["formulary"])


@router.post("/{table_slug}", response_model=CreateResponse)
def create_record(table_slug: str, req: CreateRequest):
    """Create one or more rows. Returns the created PK under a
    table-specific key (e.g. payer_id, brand_id) for FK chaining."""
    cfg = get_table_config(table_slug)
    if cfg is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown table '{table_slug}'. Available: {', '.join(sorted(SLUG_MAP.keys()))}",
        )

    payload = req.data if isinstance(req.data, list) else [req.data]

    try:
        ids = crud.create_rows(table_slug, payload)
        id_key = get_id_key(table_slug)
        # Single insert -> plain string; batch -> list
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", response_model=list[TableInfo])
def list_tables():
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
