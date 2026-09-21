"""Insert 12 test records into MAIN DB via temp API (8093). INSERT-ONLY."""
import requests

BASE = "http://127.0.0.1:8093/api/v1/formulary"
ORG = "00000000-0000-4000-8000-000000000001"  # Medivo360 Default (verified exists)

def post(slug, record):
    r = requests.post(f"{BASE}/{slug}", json={"data": record}, timeout=60)
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(f"FAILED {slug}: {d}")
    return d

# 1. Payer
p = post("payers", {"name": "Local Test Payer MAIN", "type": "Commercial",
                    "state": "Texas", "status": "Active"})
payer_id = p["payer_id"]
print(f"1. payer_id = {payer_id}")

# 2. Account (manufacturer for brand step)
acc = post("accounts", {"name": "Local Test Manufacturer MAIN", "type": "MAH",
                        "status": "Active", "organization_id": ORG})
account_id = acc["account_id"]
print(f"2. account_id = {account_id}")

# 3. Plan
pl = post("plans", {"name": "Local Test Plan MAIN", "payer_id": payer_id,
                    "type": "PPO", "plan_year": 2026, "status": "Active",
                    "active": True, "source": "Data Collection"})
plan_id = pl["plan_id"]
print(f"3. plan_id = {plan_id}")

# 4. Brand (manufacturer = created account)
b = post("brands", {"brand_id": "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
                    "name": "Local Test Brand MAIN", "generic_name": "Local Generic",
                    "product_labeler_code": "9999",
                    "manufacturer_id": account_id,
                    "status": "Active", "ignore_flag": False})
brand_id = b["brand_id"]
print(f"4. brand_id = {brand_id}")

# 5. Route
rt = post("routes", {"name": "Test Oral Route MAIN", "definition": "Main DB test",
                     "short_name": "T-ORAL-M", "fda_code": "999",
                     "nci_concept_id": "C99999"})
route_id = rt["route_id"]
print(f"5. route_id = {route_id}")

# 6. Route mapping
rm = post("route-mapping", {"mapping_id": "bbbbbbbb-3333-4333-8333-bbbbbbbbbbbb",
                            "route_of_administration_id": route_id,
                            "organization_id": ORG})
print(f"6. mapping_id = {rm['mapping_id']}")

# 7. Product
pr = post("products", {"brand_id": brand_id, "product_ndc": "9999-9999",
                       "product_id": "9999-9999_main001",
                       "dosage_form_name": "TABLET",
                       "route_of_administration_id": route_id,
                       "marketing_category_name": "NDA",
                       "application_number": "NDA999999",
                       "ndc_exclude_flag": False, "active": True,
                       "substance_name": "TESTSUBSTANCE", "ignore_flag": False})
product_id = pr["product_id"]
print(f"7. product_id = {product_id}")

# 8. Drug formulary
df = post("drug-formulary", {"coverage_status": "Covered", "drug_tier": "Tier 1",
                             "is_prior_authorization_required": False,
                             "is_step_therapy_required": False,
                             "is_quantity_limit_applied": False,
                             "status": "active",
                             "last_updated_date": "2026-09-21",
                             "drug_name": "Local Test Drug MAIN 100 mg",
                             "ocr_confidence_score": "0.95",
                             "manual_review": False, "brand_id": brand_id,
                             "product_id": product_id,
                             "expansion_status": "Not Started"})
formulary_id = df["formulary_id"]
print(f"8. formulary_id = {formulary_id}")

# 9. Coverage link
fpc = post("formulary-product-coverage", {"payer_id": payer_id, "plan_id": plan_id,
                                          "map_status": "active",
                                          "effective_date": "2026-09-21",
                                          "formulary_id": formulary_id})
print(f"9. coverage_id = {fpc['coverage_id']}")

# 10. Acronym
ac = post("acronyms", {"state": "Texas", "payer_id": payer_id,
                       "member_plan_id": plan_id, "acronym": "LTSTM",
                       "expansion": "Local Test Main", "explanation": "Main DB test.",
                       "coverage_status": "Covered"})
print(f"10. acronym_id = {ac['acronym_id']}")

# 11. Content asset
ca = post("content-assets", {"entity_type": "payer_based_plans",
                             "entity_id": plan_id,
                             "original_filename": "main-test.pdf",
                             "storage_key": "test/main/main-test.pdf",
                             "mime_type": "application/pdf",
                             "size_bytes": 0, "storage_provider": "local",
                             "active": True})
print(f"11. asset_id = {ca['asset_id']}")

# 12. Audit log
al = post("audit-log", {"name": "AUD-MAIN-001", "old_value": "Old",
                        "new_value": "New", "data_object_name": "payers",
                        "field_name": "name", "record_id": payer_id,
                        "operation_type": "CREATE"})
print(f"12. audit_id = {al['audit_id']}")

print("\nAll 12 test records inserted into MAIN DB.")
