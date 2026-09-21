"""
Request Validator — validates incoming data against DB schema constraints.
Checks: column types, max lengths, NOT NULL, CHECK constraints, UNIQUE constraints.
"""
from __future__ import annotations
from typing import Any
from app.database import get_cursor
from app.table_config import get_table_config, get_full_table_name


_column_cache: dict[str, list[dict]] = {}
_check_cache: dict[str, list[dict]] = {}
_unique_cache: dict[str, list[dict]] = {}


def _cache_key(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def _load_column_metadata(schema: str, table: str) -> list[dict]:
    key = _cache_key(schema, table)
    if key in _column_cache:
        return _column_cache[key]

    with get_cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length,
                   is_nullable, column_default, udt_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table))
        cols = cur.fetchall()

    _column_cache[key] = cols
    return cols


def _load_check_constraints(schema: str, table: str) -> list[dict]:
    key = _cache_key(schema, table)
    if key in _check_cache:
        return _check_cache[key]

    with get_cursor() as cur:
        cur.execute("""
            SELECT cc.check_clause, tc.constraint_name
            FROM information_schema.check_constraints cc
            JOIN information_schema.table_constraints tc
              ON cc.constraint_name = tc.constraint_name
             AND cc.constraint_schema = tc.table_schema
            WHERE tc.table_schema = %s AND tc.table_name = %s
        """, (schema, table))
        checks = cur.fetchall()

    _check_cache[key] = checks
    return checks


def _load_unique_constraints(schema: str, table: str) -> list[list[str]]:
    key = _cache_key(schema, table)
    if key in _unique_cache:
        return _unique_cache[key]

    with get_cursor() as cur:
        cur.execute("""
            SELECT kcu.column_name, tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s AND tc.table_name = %s
              AND tc.constraint_type = 'UNIQUE'
            ORDER BY tc.constraint_name, kcu.ordinal_position
        """, (schema, table))
        rows = cur.fetchall()

    groups: dict[str, list[str]] = {}
    for r in rows:
        cn = r["constraint_name"]
        groups.setdefault(cn, []).append(r["column_name"])

    uniques = list(groups.values())
    _unique_cache[key] = uniques
    return uniques


def _parse_check_values(check_clause: str) -> list[str] | None:
    """Extract allowed values from a CHECK clause like:
       ANY (ARRAY['val1'::text, 'val2'::text])"""
    if "ANY (ARRAY[" not in check_clause:
        return None
    import re
    matches = re.findall(r"'([^']+)'", check_clause)
    return matches if matches else None


_TYPE_MAP = {
    "uuid": "uuid",
    "character varying": "str",
    "varchar": "str",
    "text": "str",
    "integer": "int",
    "int": "int",
    "bigint": "int",
    "smallint": "int",
    "boolean": "bool",
    "numeric": "float",
    "decimal": "float",
    "double precision": "float",
    "real": "float",
    "timestamp with time zone": "datetime",
    "timestamp without time zone": "datetime",
    "date": "date",
    "time without time zone": "str",
    "time with time zone": "str",
    "jsonb": "dict",
    "json": "dict",
    "bytea": "bytes",
}


def validate_row(slug: str, row: dict[str, Any], skip_unique: bool = False) -> list[str]:
    """Validate a single row against DB schema constraints.
    Returns a list of error messages (empty = valid)."""
    cfg = get_table_config(slug)
    if cfg is None:
        return [f"Unknown slug: {slug}"]

    schema, table = cfg["schema"], cfg["table"]
    errors: list[str] = []

    columns = _load_column_metadata(schema, table)
    col_map = {c["column_name"]: c for c in columns}
    user_cols = set(cfg["user_columns"])

    # 1) Check for unknown columns
    for field in row:
        if field not in col_map:
            errors.append(f"Unknown column '{field}' on table '{schema}.{table}'")

    # 2) Check each provided field
    for field, value in row.items():
        if field not in col_map:
            continue

        col = col_map[field]
        nullable = col["is_nullable"] == "YES"
        max_len = col["character_maximum_length"]
        data_type = col["data_type"]

        # NOT NULL check
        if value is None and not nullable:
            errors.append(f"Column '{field}' cannot be NULL")
            continue

        if value is None:
            continue

        # Type checks
        expected = _TYPE_MAP.get(data_type, "str")

        if expected == "uuid" and not isinstance(value, str):
            errors.append(f"Column '{field}' must be a UUID string, got {type(value).__name__}")
        elif expected == "uuid" and isinstance(value, str):
            import uuid as uuid_mod
            try:
                uuid_mod.UUID(value)
            except ValueError:
                errors.append(f"Column '{field}' must be a valid UUID, got '{value}'")

        elif expected == "int":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"Column '{field}' must be an integer, got {type(value).__name__}")

        elif expected == "float":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"Column '{field}' must be a number, got {type(value).__name__}")

        elif expected == "bool":
            if not isinstance(value, bool):
                errors.append(f"Column '{field}' must be a boolean, got {type(value).__name__}")

        # Length check for string types
        if expected == "str" and isinstance(value, str) and max_len:
            if len(value) > max_len:
                errors.append(
                    f"Column '{field}' max length is {max_len}, got {len(value)}"
                )

    # 3) CHECK constraints — validate allowed values
    checks = _load_check_constraints(schema, table)
    for ck in checks:
        clause = ck["check_clause"]
        allowed = _parse_check_values(clause)
        if allowed is None:
            continue
        # Find which column this check applies to by matching column names in the clause
        for field, value in row.items():
            if value is None:
                continue
            if field in clause and isinstance(value, str) and value not in allowed:
                errors.append(
                    f"Column '{field}' must be one of {allowed}, got '{value}'"
                )

    # 4) UNIQUE constraints — check if value already exists
    # (skipped for UPDATE: the row itself would self-collide; DB is final arbiter)
    uniques = _load_unique_constraints(schema, table)
    if uniques and not skip_unique:
        with get_cursor() as cur:
            for uq_cols in uniques:
                provided = [c for c in uq_cols if c in row and row[c] is not None]
                if len(provided) != len(uq_cols):
                    continue
                conditions = " AND ".join([f'"{c}" = %s' for c in uq_cols])
                vals = [row[c] for c in uq_cols]
                cur.execute(
                    f'SELECT 1 FROM {schema}.{table} WHERE {conditions} LIMIT 1',
                    vals,
                )
                if cur.fetchone():
                    errors.append(
                        f"Unique constraint violated on columns {uq_cols}: "
                        f"a row with these values already exists"
                    )

    return errors


def validate_batch(slug: str, data: list[dict[str, Any]]) -> list[str]:
    """Validate all rows in a batch. Returns combined error list."""
    all_errors: list[str] = []
    for i, row in enumerate(data):
        row_errors = validate_row(slug, row)
        for err in row_errors:
            all_errors.append(f"Row {i + 1}: {err}")
    return all_errors


def validate_update(slug: str, data: dict[str, Any], partial: bool = True) -> list[str]:
    """Validate an UPDATE payload (types, lengths, CHECKs; UNIQUE skipped —
    DB enforces it and reports the real conflict)."""
    cfg = get_table_config(slug)
    if cfg is None:
        return [f"Unknown slug: {slug}"]
    if not data:
        return ["Empty update payload"]
    # PK is immutable (stripped by crud); validate everything else
    return validate_row(slug, dict(data), skip_unique=True)
