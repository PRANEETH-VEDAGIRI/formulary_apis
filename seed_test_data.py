"""Fresh test data via API (port 8092), parent->child order, named IDs."""
import requests

BASE = "http://127.0.0.1:8092/api/v1/formulary"

def post(slug, record):
    r = requests.post(f"{BASE}/{slug}", json={"data": record}, timeout=30)
    d = r.json()
    assert d.get("success"), f"FAILED {slug}: {d}"
    return d

# 1. Payer
p = post("payers", {"name": "Local Test Payer", "type": "Commercial",
                    "state": "Texas", "status": "Active"})
payer_id = p["payer_id"]
print(f"1. payer_id = {payer_id}")

# 2. Plan
pl = post("plans", {"name": "Local Test Plan", "payer_id": payer_id,
                    "type": "PPO", "plan_year": 2026, "status": "Active",
                    "active": True, "source": "Data Collection"})
plan_id = pl["plan_id"]
print(f"2. plan_id = {plan_id}")

# 3. Brand
b = post("brands", {"brand_id": "11111111-1111-4111-8111-111111111111",
                    "name": "Local Test Brand", "generic_name": "Local Generic",
                    "product_labeler_code": "9999",
                    "manufacturer_id": "22222222-2222-4222-8222-222222222222",
                    "status": "Active", "ignore_flag": False})
brand_id = b["brand_id"]
print(f"3. brand_id = {brand_id}")

# 4. Route
rt = post("routes", {"name": "Test Oral Route", "definition": "Local test",
                     "short_name": "T-ORAL", "fda_code": "999",
                     "nci_concept_id": "C99999"})
route_id = rt["route_id"]
print(f"4. route_id = {route_id}")

# 5. Route mapping
rm = post("route-mapping", {"mapping_id": "33333333-3333-4333-8333-333333333333",
                            "route_of_administration_id": route_id})
print(f"5. mapping_id = {rm['mapping_id']}")

# 6. Product
pr = post("products", {"brand_id": brand_id, "product_ndc": "9999-9999",
                       "product_id": "9999-9999_local001",
                       "dosage_form_name": "TABLET",
                       "route_of_administration_id": route_id,
                       "marketing_category_name": "NDA",
                       "application_number": "NDA999999",
                       "ndc_exclude_flag": False, "active": True,
                       "substance_name": "TESTSUBSTANCE", "ignore_flag": False})
product_id = pr["product_id"]
print(f"6. product_id = {product_id}")

# 7. Drug formulary
df = post("drug-formulary", {"coverage_status": "Covered", "drug_tier": "Tier 1",
                             "is_prior_authorization_required": False,
                             "is_step_therapy_required": False,
                             "is_quantity_limit_applied": False,
                             "status": "active",
                             "last_updated_date": "2026-09-21",
                             "drug_name": "Local Test Drug 100 mg",
                             "ocr_confidence_score": "0.95",
                             "manual_review": False, "brand_id": brand_id,
                             "product_id": product_id,
                             "expansion_status": "Not Started"})
formulary_id = df["formulary_id"]
print(f"7. formulary_id = {formulary_id}")

# 8. Formulary product coverage
fpc = post("formulary-product-coverage", {"payer_id": payer_id, "plan_id": plan_id,
                                          "map_status": "active",
                                          "effective_date": "2026-09-21",
                                          "formulary_id": formulary_id})
print(f"8. coverage_id = {fpc['coverage_id']}")

# 9. Acronym
ac = post("acronyms", {"state": "Texas", "payer_id": payer_id,
                       "member_plan_id": plan_id, "acronym": "LTST",
                       "expansion": "Local Test", "explanation": "Local test acronym.",
                       "coverage_status": "Covered"})
print(f"9. acronym_id = {ac['acronym_id']}")

# 10. Content asset
ca = post("content-assets", {"entity_type": "payer_based_plans",
                             "entity_id": plan_id,
                             "original_filename": "local-test.pdf",
                             "storage_key": "test/local/local-test.pdf",
                             "mime_type": "application/pdf",
                             "size_bytes": 0, "storage_provider": "local",
                             "active": True})
print(f"10. asset_id = {ca['asset_id']}")

# 11. Audit log
al = post("audit-log", {"name": "AUD-LOCAL-001", "old_value": "Old",
                        "new_value": "New", "data_object_name": "payers",
                        "field_name": "name", "record_id": payer_id,
                        "operation_type": "CREATE"})
print(f"11. audit_id = {al['audit_id']}")

# 12. Account
acc = post("accounts", {"name": "Local Test Account", "type": "MAH",
                        "status": "Active",
                        "organization_id": "00000000-0000-4000-8000-000000000001"})
print(f"12. account_id = {acc['account_id']}")

print("\nAll 12 tables loaded with fresh chained test data.")
