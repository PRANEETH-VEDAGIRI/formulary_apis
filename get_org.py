"""Fetch one real organization id + verify accounts row (read-only)."""
import psycopg2

MAIN = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres",
            password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")

conn = psycopg2.connect(**MAIN, connect_timeout=10)
cur = conn.cursor()
cur.execute("SELECT id, name FROM crm.organizations LIMIT 3")
rows = cur.fetchall()
print("organizations:")
for r in rows:
    print(f"  {r[0]} | {r[1]}")
conn.close()
