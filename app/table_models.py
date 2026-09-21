"""
Per-table request models + Swagger examples.

For every table slug this builds, from the LIVE DB schema:
  - CreateModel: all user columns present as fields; required ones mandatory.
    Extra (unknown) columns are FORBIDDEN so typos fail fast with 422.
  - PatchModel: same columns, all optional (partial update).
  - example: dict with EVERY user column pre-filled with a clearly-marked
    sample value, so Swagger "Try it out" shows the full shape and the user
    only edits values.

DB-free at import time — call build_table_specs() at startup (after pool init).
"""
from __future__ import annotations
from typing import Any, Union, Annotated
from pydantic import BaseModel, ConfigDict, Field, create_model
from fastapi import Body

from app.table_config import SLUG_MAP, get_table_config, get_id_key
from app.validator import _load_column_metadata


class ForbidExtra(BaseModel):
    """Base class that rejects unknown fields at validation time."""
    model_config = ConfigDict(extra="forbid")


def sample_value(data_type: str, column: str) -> Any:
    """Obviously-replaceable, correctly-typed sample for Swagger examples."""
    if data_type == "uuid":
        return "00000000-0000-0000-0000-000000000000"
    if data_type in ("integer", "int", "bigint", "smallint"):
        return 2026 if column in ("plan_year",) else 0
    if data_type in ("numeric", "decimal", "double precision", "real"):
        return 0.0
    if data_type == "boolean":
        return False
    if data_type == "date":
        return "2026-09-21"
    if data_type in ("timestamp with time zone", "timestamp without time zone"):
        return "2026-09-21T00:00:00Z"
    if data_type in ("jsonb", "json"):
        return {}
    if data_type == "bytea":
        return ""
    return f"ENTER_{column.upper()}"


def _type_hint(data_type: str):
    if data_type in ("integer", "int", "bigint", "smallint"):
        return int
    if data_type in ("numeric", "decimal", "double precision", "real"):
        return float
    if data_type == "boolean":
        return bool
    if data_type in ("jsonb", "json"):
        return dict
    return str


def build_table_specs() -> list[dict]:
    """Inspect live schema; return one spec dict per slug.

    spec keys: slug, label, func, id_key, user_columns, required_columns,
               CreateModel, PatchModel, BodyType (single|batch + example),
               example (full-column sample body).
    """
    specs = []
    for slug in sorted(SLUG_MAP.keys()):
        cfg = get_table_config(slug)
        if cfg is None:
            continue
        schema, table = cfg["schema"], cfg["table"]
        cols_meta = {c["column_name"]: c for c in _load_column_metadata(schema, table)}
        user_cols = list(cfg["user_columns"])
        required = set(cfg.get("required_columns", []))
        id_key = get_id_key(slug)
        func = slug.replace("-", "_")
        label = table.replace("_", " ")

        create_fields: dict[str, Any] = {}
        patch_fields: dict[str, Any] = {}
        example: dict[str, Any] = {}
        for col in user_cols:
            meta = cols_meta.get(col, {})
            dt = meta.get("data_type", "text")
            max_len = meta.get("character_maximum_length")
            hint = _type_hint(dt)
            tag = "REQUIRED" if col in required else "Optional"
            extra = f"max length {max_len}. " if max_len else ""
            desc = f"{tag}. {label}.{col} ({dt}). {extra}Replace the sample value."
            example[col] = sample_value(dt, col)
            if col in required:
                create_fields[col] = (hint, Field(..., description=desc))
            else:
                create_fields[col] = (hint | None, Field(default=None, description=desc))
            patch_fields[col] = (hint | None, Field(default=None, description=f"Optional. {label}.{col} ({dt}). Only sent fields change."))

        CreateModel = create_model(f"{func.title().replace('_', '')}Create", __base__=ForbidExtra, **create_fields)
        PatchModel = create_model(f"{func.title().replace('_', '')}Patch", __base__=ForbidExtra, **patch_fields)

        BodyType = Annotated[
            Union[CreateModel, list[CreateModel]],
            Body(examples=[example], description=f"One {label} row, or a list of rows for batch create. All columns shown — edit values, then Execute."),
        ]

        specs.append({
            "slug": slug, "label": label, "func": func, "id_key": id_key,
            "user_columns": user_cols, "required_columns": sorted(required),
            "CreateModel": CreateModel, "PatchModel": PatchModel,
            "BodyType": BodyType, "example": example,
        })
    return specs
