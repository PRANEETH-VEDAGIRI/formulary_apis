"""Update local tables to match remote schema + insert sample data for testing."""
import psycopg2, json
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

LOCAL = dict(host="127.0.0.1", port=5432, dbname="formulary_api_test",
             user="postgres", password="Number@56")

conn = psycopg2.connect(**LOCAL)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# 1. Update routes_of_administration to match remote schema
try:
    cur.execute("ALTER TABLE crm.routes_of_administration ADD COLUMN definition text")
except: pass
try:
    cur.execute("ALTER TABLE crm.routes_of_administration ADD COLUMN short_name varchar")
except: pass
try:
    cur.execute("ALTER TABLE crm.routes_of_administration ADD COLUMN fda_code varchar")
except: pass
try:
    cur.execute("ALTER TABLE crm.routes_of_administration ADD COLUMN nci_concept_id varchar")
except: pass
print("Updated routes_of_administration columns")

# 2. Load sample data
with open("sample_inputs.json") as f:
    data = json.load(f)

# Insert routes of administration
for r in data["routes"]["records"]:
    cur.execute("""INSERT INTO crm.routes_of_administration (name, definition, short_name, fda_code, nci_concept_id)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
        (r.get("name"), r.get("definition"), r.get("short_name"), r.get("fda_code"), r.get("nci_concept_id")))
print(f"Inserted {len(data['routes']['records'])} routes")

# Insert accounts
for r in data["accounts"]["records"]:
    cur.execute("""INSERT INTO crm.accounts (name, type, status, organization_id)
        VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
        (r["name"], r["type"], r["status"], r["organization_id"]))
print(f"Inserted {len(data['accounts']['records'])} accounts")

# Insert brands
for r in data["brands"]["records"]:
    cur.execute("""INSERT INTO crm.brands (brand_id, name, generic_name, product_labeler_code, manufacturer_id, status, ignore_flag)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
        (r["brand_id"], r["name"], r.get("generic_name"), r["product_labeler_code"],
         r["manufacturer_id"], r["status"], r.get("ignore_flag", False)))
print(f"Inserted {len(data['brands']['records'])} brands")

# Insert drug-formulary
for r in data["drug-formulary"]["records"]:
    cur.execute("""INSERT INTO crm.drug_formulary_details
        (coverage_status, drug_tier, is_prior_authorization_required, is_step_therapy_required,
         is_quantity_limit_applied, quantity_limit_details, status, last_updated_date,
         drug_name, drug_requirements, ocr_confidence_score, manual_review,
         source_file_hash, expansion_status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (r["coverage_status"], r.get("drug_tier"), r["is_prior_authorization_required"],
         r["is_step_therapy_required"], r["is_quantity_limit_applied"],
         json.dumps(r.get("quantity_limit_details")) if r.get("quantity_limit_details") else None,
         r["status"], r["last_updated_date"], r["drug_name"], r.get("drug_requirements"),
         r.get("ocr_confidence_score"), r.get("manual_review", False),
         r.get("source_file_hash"), r.get("expansion_status", "Not Started")))
print(f"Inserted {len(data['drug-formulary']['records'])} drug-formulary records")

# Insert audit-log
for r in data["audit-log"]["records"]:
    cur.execute("""INSERT INTO crm.audit_log (name, old_value, data_object_name, field_name, record_id, operation_type)
        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (r["name"], r.get("old_value"), r["data_object_name"], r.get("field_name"),
         r.get("record_id"), r.get("operation_type")))
print(f"Inserted {len(data['audit-log']['records'])} audit-log records")

# Insert content-assets
for r in data["content-assets"]["records"]:
    cur.execute("""INSERT INTO crm.content_assets
        (entity_type, entity_id, original_filename, storage_key, mime_type, size_bytes, storage_provider, active)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (r["entity_type"], r.get("entity_id"), r["original_filename"], r["storage_key"],
         r.get("mime_type"), r.get("size_bytes", 0), r.get("storage_provider", "s3"), r.get("active", True)))
print(f"Inserted {len(data['content-assets']['records'])} content-assets")

# Show final counts
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='crm' ORDER BY tablename")
for (t,) in cur.fetchall():
    cur.execute(f"SELECT COUNT(*) FROM crm.{t}")
    print(f"  crm.{t}: {cur.fetchone()[0]} rows")

conn.close()
print("\nDone! Sample data loaded.")
