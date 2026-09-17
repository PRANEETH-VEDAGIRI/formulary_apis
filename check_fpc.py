import psycopg2
conn = psycopg2.connect(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres", password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")
cur = conn.cursor()
cur.execute("""SELECT column_name, data_type FROM information_schema.columns
               WHERE table_schema='crm' AND table_name='formulary_product_coverage'
               ORDER BY ordinal_position""")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")
conn.close()
