"""
Copy schema from remote RDS (port 5438) to local PG (port 5432).
Creates 'formulary_api_test' on local PG with same 10 tables.
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Remote (source of schema)
REMOTE = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres",
              password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")

# Local (target)
LOCAL = dict(host="127.0.0.1", port=5432, dbname="postgres", user="postgres",
             password="Number@56")
TEST_DB = "formulary_api_test"

# 1. Create test DB on local PG
conn = psycopg2.connect(**LOCAL)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
cur.execute(f"CREATE DATABASE {TEST_DB}")
print(f"Created local DB: {TEST_DB}")
conn.close()

# 2. Connect to local test DB
conn = psycopg2.connect(host=LOCAL["host"], port=LOCAL["port"], dbname=TEST_DB,
                        user=LOCAL["user"], password=LOCAL["password"])
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
cur.execute("CREATE SCHEMA IF NOT EXISTS crm")

# 3. Connect to remote to read schema
conn_r = psycopg2.connect(**REMOTE)
conn_r.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur_r = conn_r.cursor()

# Get the 10 formulary tables
TABLES = [
    "payers", "payer_based_plans", "drug_formulary_details",
    "acronym_details", "accounts", "brands", "product_details",
    "formulary_product_coverage", "content_assets", "audit_log",
]

for table in TABLES:
    # Get columns from remote
    cur_r.execute("""
        SELECT column_name, data_type, is_nullable, column_default,
               character_maximum_length, numeric_precision
        FROM information_schema.columns
        WHERE table_schema = 'crm' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    cols = cur_r.fetchall()

    # Build CREATE TABLE
    col_defs = []
    for c in cols:
        name, dtype, nullable, default, max_len, num_prec = c
        col_sql = f'"{name}" '
        type_map = {
            "character varying": f"varchar({max_len})" if max_len else "varchar",
            "character": f"char({max_len})" if max_len else "char",
            "uuid": "uuid",
            "jsonb": "jsonb",
            "bigint": "bigint",
            "boolean": "boolean",
            "smallint": "smallint",
            "integer": "integer",
            "timestamp with time zone": "timestamptz",
            "time without time zone": "time",
            "date": "date",
            "numeric": f"numeric({num_prec})" if num_prec else "numeric",
        }
        col_sql += type_map.get(dtype, dtype)
        if nullable == "NO":
            col_sql += " NOT NULL"
        if default:
            col_sql += f" DEFAULT {default}"
        col_defs.append(col_sql)

    create_sql = f"CREATE TABLE IF NOT EXISTS crm.{table} (\n  " + ",\n  ".join(col_defs) + "\n)"
    try:
        cur.execute(create_sql)
        print(f"  Created: crm.{table}")
    except Exception as e:
        print(f"  ERR {table}: {e}")

# 4. Copy primary keys
for table in TABLES:
    cur_r.execute("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'crm' AND tc.table_name = %s
        AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
    """, (table,))
    pk_cols = [r[0] for r in cur_r.fetchall()]
    if pk_cols:
        pk_str = ", ".join([f'"{c}"' for c in pk_cols])
        try:
            cur.execute(f"ALTER TABLE crm.{table} ADD PRIMARY KEY ({pk_str})")
            print(f"  PK: crm.{table}")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"  PK err {table}: {e}")

# 5. Copy unique constraints
for table in TABLES:
    cur_r.execute("""
        SELECT tc.constraint_name, string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position)
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'crm' AND tc.table_name = %s
        AND tc.constraint_type = 'UNIQUE'
        GROUP BY tc.constraint_name
    """, (table,))
    for cname, cols in cur_r.fetchall():
        try:
            cur.execute(f'ALTER TABLE crm.{table} ADD CONSTRAINT "{cname}" UNIQUE ({cols})')
        except Exception:
            pass

# 6. Copy foreign keys
for table in TABLES:
    cur_r.execute("""
        SELECT tc.constraint_name, kcu.column_name,
               ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_schema = 'crm' AND tc.table_name = %s
        AND tc.constraint_type = 'FOREIGN KEY'
    """, (table,))
    for row in cur_r.fetchall():
        cname, col, ftable, fcol = row
        try:
            cur.execute(f"""
                ALTER TABLE crm.{table} ADD CONSTRAINT "{cname}"
                FOREIGN KEY ("{col}") REFERENCES crm.{ftable}("{fcol}")
            """)
        except Exception:
            pass

# 7. Copy sequences
cur_r.execute("""
    SELECT sequence_name FROM information_schema.sequences
    WHERE sequence_schema = 'crm'
""")
for (sname,) in cur_r.fetchall():
    try:
        cur.execute(f"CREATE SEQUENCE IF NOT EXISTS crm.{sname}")
    except Exception:
        pass

# 8. Copy trigger functions
cur_r.execute("""
    SELECT p.proname, pg_get_functiondef(p.oid)
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'crm'
""")
for fname, fdef in cur_r.fetchall():
    try:
        cur.execute(f"DROP FUNCTION IF EXISTS crm.{fname} CASCADE")
        cur.execute(fdef)
        print(f"  Function: crm.{fname}")
    except Exception as e:
        pass

# 9. Copy triggers
for table in TABLES:
    cur_r.execute(f"""
        SELECT trigger_name, event_manipulation, action_timing, action_statement
        FROM information_schema.triggers
        WHERE event_object_schema = 'crm' AND event_object_table = '{table}'
    """)
    for tname, Manipulation, timing, action in cur_r.fetchall():
        try:
            cur.execute(f"DROP TRIGGER IF EXISTS {tname} ON crm.{table}")
            cur.execute(f"CREATE TRIGGER {tname} {timing} {Manipulation} ON crm.{table} {action}")
            print(f"  Trigger: {tname} on {table}")
        except Exception:
            pass

conn_r.close()

# 10. Verify
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='crm' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print(f"\nLocal test DB '{TEST_DB}' has {len(tables)} tables:")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM crm.{t}")
    print(f"  crm.{t}: {cur.fetchone()[0]} rows")

conn.close()
print("\nDone! Local DB ready on port 5432.")
