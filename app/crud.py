"""Full CRUD engine — INSERT, SELECT, UPDATE, DELETE with DB-owned IDs."""
from __future__ import annotations
from typing import Any
from app.database import get_cursor
from app.table_config import get_table_config, get_full_table_name
from config import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX


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


# ── READ ───────────────────────────────────────────────────────────────────

def _table_has_column(cur, schema: str, table: str, column: str) -> bool:
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
    """, (schema, table, column))
    return cur.fetchone() is not None


def _sanitize_row(row: dict) -> dict:
    """Convert UUID/datetime/bytes to strings for JSON-safe responses."""
    out = {}
    for k, v in row.items():
        try:
            import uuid as _uuid, datetime as _dt
            if isinstance(v, (_uuid.UUID, _dt.datetime, _dt.date, _dt.time)):
                out[k] = str(v)
            elif isinstance(v, (bytes, bytearray)):
                out[k] = v.hex()
            else:
                out[k] = v
        except Exception:
            out[k] = str(v)
    return out


def get_rows(
    slug: str,
    filters: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
) -> tuple[list[dict], int]:
    """Paginated SELECT with exact-match filters (allowlisted to real columns).
    Orders by created_at DESC when present, else by PK. Returns (rows, total)."""
    cfg = get_table_config(slug)
    if cfg is None:
        raise ValueError(f"Unknown slug: {slug}")

    tbl = get_full_table_name(cfg)
    page_size = min(max(1, page_size), PAGE_SIZE_MAX)
    offset = (max(1, page) - 1) * page_size

    with get_cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (cfg["schema"], cfg["table"]))
        real_cols = {r["column_name"] for r in cur.fetchall()}

        unknown = sorted([k for k in (filters or {}) if k not in real_cols])
        if unknown:
            raise ValueError(
                f"Unknown filter column(s): {unknown}. "
                f"Valid columns: {sorted(real_cols)}"
            )
        safe_filters = dict(filters or {})

        where_clause = ""
        where_values: list[Any] = []
        if safe_filters:
            where_clause = "WHERE " + " AND ".join([f'"{k}" = %s' for k in safe_filters])
            where_values = list(safe_filters.values())

        cur.execute(f"SELECT COUNT(*) AS cnt FROM {tbl} {where_clause}", where_values)
        total = cur.fetchone()["cnt"]

        pk = _get_pk_column(cur, cfg["schema"], cfg["table"])
        order_col = "created_at" if _table_has_column(cur, cfg["schema"], cfg["table"], "created_at") else pk

        cur.execute(
            f'SELECT * FROM {tbl} {where_clause} ORDER BY "{order_col}" DESC LIMIT %s OFFSET %s',
            where_values + [page_size, offset],
        )
        rows = [_sanitize_row(dict(r)) for r in cur.fetchall()]

    return rows, total


def get_row_by_id(slug: str, row_id: str) -> dict | None:
    """Fetch one row by PK (dynamic PK detection — composite-PK safe)."""
    cfg = get_table_config(slug)
    if cfg is None:
        raise ValueError(f"Unknown slug: {slug}")

    tbl = get_full_table_name(cfg)
    with get_cursor() as cur:
        pk = _get_pk_column(cur, cfg["schema"], cfg["table"])
        cur.execute(f'SELECT * FROM {tbl} WHERE "{pk}" = %s', (row_id,))
        result = cur.fetchone()

    return _sanitize_row(dict(result)) if result else None


# ── UPDATE ─────────────────────────────────────────────────────────────────

def update_row(slug: str, row_id: str, data: dict, partial: bool = True) -> str | None:
    """UPDATE by PK. Never touches the PK itself (DB owns IDs).
    partial=True → PATCH (only sent fields); False → PUT (all user cols, None for missing)."""
    cfg = get_table_config(slug)
    if cfg is None:
        raise ValueError(f"Unknown slug: {slug}")

    tbl = get_full_table_name(cfg)
    user_cols = cfg["user_columns"]

    if partial:
        updates = {k: v for k, v in data.items() if k in user_cols}
    else:
        updates = {col: data.get(col) for col in user_cols}

    if not updates:
        raise ValueError(f"No valid columns to update. Expected one of: {user_cols}")

    with get_cursor() as cur:
        pk = _get_pk_column(cur, cfg["schema"], cfg["table"])
        updates.pop(pk, None)  # PK is immutable — DB owns it
        if not updates:
            raise ValueError(f"Cannot update primary key '{pk}'. Provide user columns: {user_cols}")

        set_clause = ", ".join([f'"{k}" = %s' for k in updates])
        values = list(updates.values()) + [row_id]

        touch = ", updated_at = now()" if _table_has_column(cur, cfg["schema"], cfg["table"], "updated_at") else ""
        cur.execute(
            f'UPDATE {tbl} SET {set_clause}{touch} WHERE "{pk}" = %s RETURNING "{pk}"',
            values,
        )
        result = cur.fetchone()

    return str(result[pk]) if result else None


# ── DELETE ─────────────────────────────────────────────────────────────────

def delete_row(slug: str, row_id: str) -> bool:
    """DELETE by PK. FK RESTRICT / trigger blocks raise naturally —
    routes map those to HTTP 409 so callers get a clean conflict message."""
    cfg = get_table_config(slug)
    if cfg is None:
        raise ValueError(f"Unknown slug: {slug}")

    tbl = get_full_table_name(cfg)
    with get_cursor() as cur:
        pk = _get_pk_column(cur, cfg["schema"], cfg["table"])
        cur.execute(f'DELETE FROM {tbl} WHERE "{pk}" = %s RETURNING "{pk}"', (row_id,))
        result = cur.fetchone()

    return result is not None
