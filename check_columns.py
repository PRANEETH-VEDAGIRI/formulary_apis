"""Get column info for all 10 formulary tables."""
import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres", password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")
cur = conn.cursor()

tables = [
    ("crm", "payers"),
    ("crm", "payer_based_plans"),
    ("crm", "drug_formulary_details"),
    ("crm", "acronym_details"),
    ("crm", "accounts"),
    ("crm", "brands"),
    ("crm", "product_details"),
    ("crm", "formulary_product_coverage"),
    ("crm", "content_assets"),
    ("crm", "audit_log"),
]

for schema, table in tables:
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema, table))
    cols = cur.fetchall()
    print(f"\n=== {schema}.{table} ===")
    for c in cols:
        auto = "AUTO" if c[3] or c[0] in ("id", "created_at", "updated_at", "created_by", "modified_by") else "USER"
        print(f"  {c[0]:40s} {c[1]:30s} nullable={c[2]:3s} default={str(c[3])[:40]:40s} [{auto}]")

conn.close()
