"""CREATE-only CRUD engine — inserts rows, returns created IDs."""
from __future__ import annotations
from typing import Any
from app.database import get_cursor
from app.table_config import get_table_config, get_full_table_name


def create_rows(slug: str, data: list[dict]) -> list[str]:
    """Insert rows and return the created IDs."""
    cfg = get_table_config(slug)
    if cfg is None:
        raise ValueError(f"Unknown slug: {slug}")

    tbl = get_full_table_name(cfg)
    user_cols = cfg["user_columns"]

    if not data:
        return []

    filtered = [{k: v for k, v in row.items() if k in user_cols} for row in data]
    filtered = [r for r in filtered if r]

    if not filtered:
        raise ValueError(f"No valid user columns provided. Expected: {user_cols}")

    ids = []
    with get_cursor() as cur:
        for row in filtered:
            cols = list(row.keys())
            col_str = ", ".join([f'"{c}"' for c in cols])
            placeholders = ", ".join(["%s"] * len(cols))
            values = [row[c] for c in cols]
            cur.execute(
                f"INSERT INTO {tbl} ({col_str}) VALUES ({placeholders}) RETURNING id",
                values,
            )
            result = cur.fetchone()
            if result:
                ids.append(str(result["id"]))
    return ids


def create_rows_bulk(slug: str, data: list[dict], batch_size: int = 500) -> list[str]:
    """Bulk insert using executemany, return created IDs."""
    cfg = get_table_config(slug)
    if cfg is None:
        raise ValueError(f"Unknown slug: {slug}")

    tbl = get_full_table_name(cfg)
    user_cols = cfg["user_columns"]

    if not data:
        return []

    filtered = [{k: v for k, v in row.items() if k in user_cols} for row in data]
    filtered = [r for r in filtered if r]

    if not filtered:
        raise ValueError(f"No valid user columns provided. Expected: {user_cols}")

    ids = []
    with get_cursor() as cur:
        for row in filtered:
            cols = list(row.keys())
            col_str = ", ".join([f'"{c}"' for c in cols])
            placeholders = ", ".join(["%s"] * len(cols))
            values = [row[c] for c in cols]
            cur.execute(
                f"INSERT INTO {tbl} ({col_str}) VALUES ({placeholders}) RETURNING id",
                values,
            )
            result = cur.fetchone()
            if result:
                ids.append(str(result["id"]))
    return ids
