"""Read-only pre-checks on main DB before inserting test data."""
import psycopg2

MAIN = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres",
            password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")

conn = psycopg2.connect(**MAIN, connect_timeout=10)
cur = conn.cursor()

TABLES = ["payers", "payer_based_plans", "drug_formulary_details",
          "acronym_details", "accounts", "brands", "product_details",
          "formulary_product_coverage", "content_assets", "audit_log",
          "routes_of_administration", "route_mapping"]

print("Table existence + row counts (approx via pg_stat):")
for t in TABLES:
    cur.execute("SELECT to_regclass(%s)", (f"crm.{t}",))
    exists = cur.fetchone()[0]
    if exists:
        cur.execute("SELECT n_live_tup FROM pg_stat_user_tables WHERE schemaname='crm' AND relname=%s", (t,))
        r = cur.fetchone()
        print(f"  crm.{t}: EXISTS (~{r[0] if r else '?'} rows)")
    else:
        print(f"  crm.{t}: MISSING!")

print("\nNOT NULL columns without defaults (must be provided):")
for t in TABLES:
    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema='crm' AND table_name=%s
          AND is_nullable='NO' AND column_default IS NULL
          AND column_name NOT IN ('id','created_at','updated_at','created_by','modified_by')
        ORDER BY ordinal_position""", (t,))
    cols = cur.fetchall()
    print(f"  crm.{t}: {[(c[0], c[1]) for c in cols] or 'none'}")

print("\nroute_mapping full columns:")
cur.execute("""SELECT column_name, data_type, is_nullable FROM information_schema.columns
               WHERE table_schema='crm' AND table_name='route_mapping' ORDER BY ordinal_position""")
for r in cur.fetchall():
    print(f"  {r}")

print("\nroutes_of_administration full columns:")
cur.execute("""SELECT column_name, data_type, is_nullable FROM information_schema.columns
               WHERE table_schema='crm' AND table_name='routes_of_administration' ORDER BY ordinal_position""")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
print("\nPre-check done. No writes performed.")
