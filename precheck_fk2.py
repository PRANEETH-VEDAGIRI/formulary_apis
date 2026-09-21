"""Distinct FK constraints on main DB (read-only)."""
import psycopg2

MAIN = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres",
            password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")

conn = psycopg2.connect(**MAIN, connect_timeout=10)
cur = conn.cursor()
cur.execute("""
    SELECT DISTINCT tc.table_name, kcu.column_name,
           ccu.table_name AS ref_table, ccu.column_name AS ref_col
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_name = kcu.table_name
    JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema='crm' AND tc.constraint_type='FOREIGN KEY'
      AND tc.table_name IN ('brands','accounts','route_mapping','product_details',
        'drug_formulary_details','payer_based_plans','acronym_details',
        'formulary_product_coverage','content_assets','routes_of_administration',
        'payers','audit_log')
    ORDER BY 1, 2""")
seen = set()
for t, c, rt, rc in cur.fetchall():
    key = (t, c, rt, rc)
    if key not in seen:
        seen.add(key)
        print(f"  {t}.{c} -> {rt}.{rc}")
conn.close()
