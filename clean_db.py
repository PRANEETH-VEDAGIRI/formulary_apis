import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="formulary_api_test",
                        user="postgres", password="Number@56")
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='crm' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]

for t in tables:
    cur.execute(f"TRUNCATE crm.{t} RESTART IDENTITY CASCADE")
    print(f"  Truncated crm.{t}")

print("\nVerifying:")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM crm.{t}")
    print(f"  crm.{t}: {cur.fetchone()[0]} rows")

conn.close()
print("\nLocal DB clean.")
