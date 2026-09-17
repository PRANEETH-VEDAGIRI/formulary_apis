import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="formulary_api_test",
                        user="postgres", password="Number@56")
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS crm.routes_of_administration (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid, modified_by uuid
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS crm.route_mapping (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mapping_id uuid NOT NULL,
    route_of_administration_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid, modified_by uuid
)""")

cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='crm' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables in local DB ({len(tables)}):")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM crm.{t}")
    print(f"  crm.{t} - {cur.fetchone()[0]} rows")

conn.close()
