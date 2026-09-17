import requests
BASE = "http://127.0.0.1:8080/api/v1/formulary"

tests = [
    ("acronyms", {"acronym": "TEST", "state": "TX", "payer_id": "00000000-0000-0000-0000-000000000000", "member_plan_id": "00000000-0000-0000-0000-000000000000"}),
    ("accounts", {"name": "TEST", "type": "Test", "organization_id": "00000000-0000-0000-0000-000000000000"}),
    ("brands", {"brand_id": "00000000-0000-0000-0000-000000000000", "name": "TEST", "product_labeler_code": "123", "manufacturer_id": "00000000-0000-0000-0000-000000000000", "status": "Active"}),
    ("products", {"brand_id": "00000000-0000-0000-0000-000000000000", "product_ndc": "12345-1234-01", "product_id": "TEST"}),
    ("formulary-product-coverage", {"payer_id": "00000000-0000-0000-0000-000000000000", "plan_id": "00000000-0000-0000-0000-000000000000", "formulary_id": "00000000-0000-0000-0000-000000000000"}),
]

for slug, data in tests:
    r = requests.post(f"{BASE}/{slug}", json={"data": data}, timeout=30)
    print(f"  [{r.status_code}] {slug}: {r.text[:200]}")
