import psycopg2
import json

REMOTE = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres",
              password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")

TABLES = {
    "payers":                 "crm.payers",
    "plans":                  "crm.payer_based_plans",
    "drug-formulary":         "crm.drug_formulary_details",
    "acronyms":               "crm.acronym_details",
    "accounts":               "crm.accounts",
    "brands":                 "crm.brands",
    "products":               "crm.product_details",
    "formulary-product-coverage": "crm.formulary_product_coverage",
    "content-assets":         "crm.content_assets",
    "audit-log":              "crm.audit_log",
    "routes":                 "crm.routes_of_administration",
    "route-mapping":          "crm.route_mapping",
}

SKIP = {"id", "created_at", "updated_at", "created_by", "modified_by"}

conn = psycopg2.connect(**REMOTE)
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

results = {}
for slug, table in TABLES.items():
    try:
        cur.execute(f"SELECT * FROM {table} LIMIT 5")
        cols = [d[0] for d in cur.description]
        user_cols = [c for c in cols if c not in SKIP]
        rows = []
        for row in cur.fetchall():
            record = {}
            for i, c in enumerate(user_cols):
                val = row[cols.index(c)]
                if val is None:
                    continue
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                elif isinstance(val, (dict, list)):
                    pass
                elif not isinstance(val, (str, int, float, bool)):
                    val = str(val)
                record[c] = val
            rows.append(record)
        results[slug] = {"table": table, "columns": user_cols, "records": rows}
        print(f"  {slug}: {len(rows)} records")
    except Exception as e:
        print(f"  {slug}: ERROR - {e}")
        results[slug] = {"table": table, "error": str(e)}

conn.close()

with open("sample_inputs.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved to sample_inputs.json")
