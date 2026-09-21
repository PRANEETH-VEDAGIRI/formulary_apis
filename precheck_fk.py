"""Check FK constraints on main DB for columns we will insert."""
import psycopg2

MAIN = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres",
            password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")

conn = psycopg2.connect(**MAIN, connect_timeout=10)
cur = conn.cursor()
cur.execute("""
    SELECT tc.table_name, kcu.column_name,
           ccu.table_name AS ref_table, ccu.column_name AS ref_col
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema='crm' AND tc.constraint_type='FOREIGN KEY'
      AND tc.table_name IN ('brands','accounts','route_mapping','product_details',
        'drug_formulary_details','payer_based_plans','acronym_details',
        'formulary_product_coverage','content_assets')
    ORDER BY tc.table_name, kcu.column_name""")
rows = cur.fetchall()
print("FK constraints:")
for r in rows:
    print(f"  {r[0]}.{r[1]} -> {r[2]}.{r[3]}")
if not rows:
    print("  none found")
conn.close()
