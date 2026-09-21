"""
Table configuration — slug → table mapping.
Each table defines: schema, table, user_input columns (what API consumer provides).
Auto-generated columns (id, created_at, updated_at, etc.) are DB-handled.
"""
from psycopg2.extras import RealDictCursor
from app.database import get_cursor


def _get_user_columns(schema: str, table: str) -> list[str]:
    """Auto-detect user-input columns: NOT NULL without defaults + nullable user cols."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table))
        cols = []
        for r in cur.fetchall():
            name = r["column_name"]
            nullable = r["is_nullable"] == "YES"
            has_default = r["column_default"] is not None
            # Skip auto-generated: id, timestamps, created_by, modified_by, booleans with defaults
            if name in ("id", "created_at", "updated_at", "created_by", "modified_by"):
                continue
            if has_default and not nullable:
                continue  # has DB default, user doesn't need to provide
            cols.append(name)
        return cols


# Lazy-loaded table configs (populated on first access)
_TABLE_CONFIGS: dict = {}
_LOADED = False

SLUG_MAP = {
    "payers":                  ("crm", "payers"),
    "plans":                   ("crm", "payer_based_plans"),
    "drug-formulary":          ("crm", "drug_formulary_details"),
    "acronyms":                ("crm", "acronym_details"),
    "accounts":                ("crm", "accounts"),
    "brands":                  ("crm", "brands"),
    "products":                ("crm", "product_details"),
    "formulary-product-coverage": ("crm", "formulary_product_coverage"),
    "content-assets":          ("crm", "content_assets"),
    "audit-log":               ("crm", "audit_log"),
    "routes":                  ("crm", "routes_of_administration"),
    "route-mapping":           ("crm", "route_mapping"),
}

# Semantic name for the created PK, per slug — used as the response key
# so callers know exactly which ID they got back for FK chaining.
ID_KEYS = {
    "payers":                     "payer_id",
    "plans":                      "plan_id",
    "drug-formulary":             "formulary_id",
    "acronyms":                   "acronym_id",
    "accounts":                   "account_id",
    "brands":                     "brand_id",
    "products":                   "product_id",
    "formulary-product-coverage": "coverage_id",
    "content-assets":             "asset_id",
    "audit-log":                  "audit_id",
    "routes":                     "route_id",
    "route-mapping":              "mapping_id",
}


def get_id_key(slug: str) -> str:
    return ID_KEYS.get(slug, "id")


_AUTO_SKIP = ("id", "created_at", "updated_at", "created_by", "modified_by")


def _get_pk_column(schema: str, table: str) -> str:
    """Primary key column (first column of PK; composite-PK safe)."""
    with get_cursor() as cur:
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


def get_required_columns(schema: str, table: str) -> list[str]:
    """Columns the caller MUST supply: NOT NULL with no DB default,
    excluding auto-handled columns. Cached per table."""
    _ensure_loaded()
    for _slug, _cfg in _TABLE_CONFIGS.items():
        if _cfg["schema"] == schema and _cfg["table"] == table:
            return list(_cfg.get("required_columns", []))
    return []


def _get_required_columns(schema: str, table: str) -> list[str]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table))
        req = []
        for r in cur.fetchall():
            name = r["column_name"]
            if name in _AUTO_SKIP:
                continue
            if r["is_nullable"] == "YES":
                continue
            if r["column_default"] is not None:
                continue
            req.append(name)
        return req


def _ensure_loaded():
    global _LOADED
    if _LOADED:
        return
    for slug, (schema, table) in SLUG_MAP.items():
        user_cols = _get_user_columns(schema, table)
        _TABLE_CONFIGS[slug] = {
            "schema": schema,
            "table": table,
            "user_columns": user_cols,
            "required_columns": _get_required_columns(schema, table),
            "pk_column": _get_pk_column(schema, table),
        }
    _LOADED = True


def get_table_config(slug: str) -> dict | None:
    _ensure_loaded()
    return _TABLE_CONFIGS.get(slug)


def get_all_configs() -> dict:
    _ensure_loaded()
    return _TABLE_CONFIGS


def get_full_table_name(cfg: dict) -> str:
    return f"{cfg['schema']}.{cfg['table']}"
