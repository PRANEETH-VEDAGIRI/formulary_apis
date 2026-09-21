"""CREATE-only CRUD engine — inserts rows, returns created IDs."""
from __future__ import annotations
from typing import Any
from app.database import get_cursor
from app.table_config import get_table_config, get_full_table_name


def _get_pk_column(cur, schema: str, table: str) -> str:
    """Find the primary key column; fall back to 'id'."""
    cur.execute("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_name = kcu.table_name
        WHERE tc.table_schema = %s AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position LIMIT 1
    """, (schema, table))
    row = cur.fetchone()
    if row:
        return row["column_name"] if isinstance(row, dict) else row[0]
    return "id"


def _pk_has_default(cur, schema: str, table: str, pk: str) -> bool:
    """True if the PK column has a DB default (gen_random_uuid, uuid_generate_v4, etc).
    If True, DB is fully responsible for generating the ID."""
    cur.execute("""
        SELECT column_default FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
    """, (schema, table, pk))
    row = cur.fetchone()
    if not row:
        return False
    default = row["column_default"] if isinstance(row, dict) else row[0]
    return default is not None


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
        pk = _get_pk_column(cur, cfg["schema"], cfg["table"])
        # DB owns ID generation: drop any client-supplied PK if DB has a default.
        # RETURNING always gives back the DB-created ID — no conflict possible.
        db_generates = _pk_has_default(cur, cfg["schema"], cfg["table"], pk)
        for row in filtered:
            if db_generates and pk in row:
                row = {k: v for k, v in row.items() if k != pk}
            if not row:
                raise ValueError(
                    f"No insertable columns for '{slug}'. "
                    f"DB auto-generates '{pk}' — provide user columns: {user_cols}"
                )
            cols = list(row.keys())
            col_str = ", ".join([f'"{c}"' for c in cols])
            placeholders = ", ".join(["%s"] * len(cols))
            values = [row[c] for c in cols]
            cur.execute(
                f'INSERT INTO {tbl} ({col_str}) VALUES ({placeholders}) RETURNING "{pk}"',
                values,
            )
            result = cur.fetchone()
            if result:
                ids.append(str(result[pk]))
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
        pk = _get_pk_column(cur, cfg["schema"], cfg["table"])
        db_generates = _pk_has_default(cur, cfg["schema"], cfg["table"], pk)
        for row in filtered:
            if db_generates and pk in row:
                row = {k: v for k, v in row.items() if k != pk}
            if not row:
                raise ValueError(
                    f"No insertable columns for '{slug}'. "
                    f"DB auto-generates '{pk}' — provide user columns: {user_cols}"
                )
            cols = list(row.keys())
            col_str = ", ".join([f'"{c}"' for c in cols])
            placeholders = ", ".join(["%s"] * len(cols))
            values = [row[c] for c in cols]
            cur.execute(
                f'INSERT INTO {tbl} ({col_str}) VALUES ({placeholders}) RETURNING "{pk}"',
                values,
            )
            result = cur.fetchone()
            if result:
                ids.append(str(result[pk]))
    return ids
