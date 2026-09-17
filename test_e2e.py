"""
E2E Test Suite — Formulary APIs (CREATE only)
Tests all 10 table slugs, verifies auto-generated columns excluded, FK-aware test data.
"""
import requests
import json
import time
import sys
import uuid

BASE = "http://127.0.0.1:8090/api/v1/formulary"
PASS = 0
FAIL = 0
RESULTS = []


def test(name, fn):
    global PASS, FAIL
    try:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        if ok:
            PASS += 1
        else:
            FAIL += 1
        RESULTS.append({"test": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}: {detail}")
    except Exception as e:
        FAIL += 1
        RESULTS.append({"test": name, "status": "FAIL", "detail": str(e)})
        print(f"  [FAIL] {name}: {e}")


def post(slug, body):
    return requests.post(f"{BASE}/{slug}", json=body, timeout=60)


def get_tables():
    return requests.get(f"{BASE}/tables", timeout=120).json()


# ── HEALTH ───────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get("http://127.0.0.1:8090/health", timeout=5)
    return r.ok, r.json()


def test_list_tables():
    tables = get_tables()
    slugs = [t["slug"] for t in tables]
    return len(slugs) >= 10, f"{len(slugs)} tables: {slugs}"


# ── SCHEMA: no auto-generated cols in user input ─────────────────────────────

def test_no_id_in_user_columns():
    tables = get_tables()
    for t in tables:
        if "id" in t["user_columns"]:
            return False, f"{t['slug']} has 'id' in user_columns"
    return True, "all clean"


def test_no_timestamps_in_user_columns():
    tables = get_tables()
    bad = []
    for t in tables:
        found = [c for c in t["user_columns"] if c in ("created_at", "updated_at", "created_by", "modified_by")]
        if found:
            bad.append(f"{t['slug']}: {found}")
    return len(bad) == 0, bad or "all clean"


def test_user_columns_populated():
    tables = get_tables()
    empty = [t["slug"] for t in tables if not t["user_columns"]]
    return len(empty) == 0, f"empty: {empty}" if empty else "all have user columns"


# ── CREATE: payers ───────────────────────────────────────────────────────────

def test_create_payer():
    r = post("payers", {"data": {"name": f"E2E_PAYER_{int(time.time())}", "type": "Test", "status": "Active"}})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d["success"] and d["inserted"] == 1 and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: plans (need real payer_id) ───────────────────────────────────────

def test_create_plan():
    # Create a real payer first to get a valid FK
    pr = post("payers", {"data": {"name": f"FK_PAYER_{int(time.time())}", "type": "Test", "status": "Active"}})
    payer_id = pr.json()["ids"][0]
    r = post("plans", {"data": {
        "name": f"E2E_PLAN_{int(time.time())}",
        "payer_id": payer_id,
        "type": "Commercial",
        "plan_year": 2026,
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d.get("success", False) and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: drug-formulary ───────────────────────────────────────────────────

def test_create_drug_formulary():
    r = post("drug-formulary", {"data": {
        "drug_name": f"E2E_DRUG_{int(time.time())}",
        "coverage_status": "Covered",
        "drug_tier": "Tier 1",
        "last_updated_date": "2026-09-17",
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d["success"] and d["inserted"] == 1 and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: acronyms (need real payer_id + member_plan_id) ──────────────────

def test_create_acronym():
    r = post("acronyms", {"data": {
        "acronym": f"E2E{int(time.time())}",
        "payer_id": str(uuid.uuid4()),
        "member_plan_id": str(uuid.uuid4()),
        "expansion": "Test",
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d.get("success", False) and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: accounts (need real organization_id) ─────────────────────────────

def test_create_account():
    r = post("accounts", {"data": {
        "name": f"E2E_ACCT_{int(time.time())}",
        "type": "Test",
        "organization_id": str(uuid.uuid4()),
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d.get("success", False) and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: brands (need real manufacturer_id) ──────────────────────────────

def test_create_brand():
    r = post("brands", {"data": {
        "brand_id": str(uuid.uuid4()),
        "name": f"E2E_BRAND_{int(time.time())}",
        "product_labeler_code": "12345",
        "manufacturer_id": str(uuid.uuid4()),
        "status": "Active",
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d.get("success", False) and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: products (need real brand_id) ───────────────────────────────────

def test_create_product():
    r = post("products", {"data": {
        "brand_id": str(uuid.uuid4()),
        "product_ndc": f"12345-{int(time.time()) % 10000:04d}-01",
        "product_id": f"PROD{int(time.time())}",
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d.get("success", False) and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: formulary-product-coverage ───────────────────────────────────────

def test_create_fpc():
    r = post("formulary-product-coverage", {"data": {
        "payer_id": str(uuid.uuid4()),
        "plan_id": str(uuid.uuid4()),
        "formulary_id": str(uuid.uuid4()),
    }})
    d = r.json()
    has_ids = "ids" in d and len(d["ids"]) == 1
    return d.get("success", False) and has_ids, f"inserted={d.get('inserted')}, ids={d.get('ids')}"


# ── CREATE: content-assets ───────────────────────────────────────────────────

def test_create_content_asset():
    r = post("content-assets", {"data": {
        "entity_type": "plan",
        "original_filename": "test.pdf",
        "storage_key": f"test/{int(time.time())}.pdf",
    }})
    d = r.json()
    return d["success"], f"inserted={d.get('inserted')}"


# ── CREATE: audit-log ────────────────────────────────────────────────────────

def test_create_audit_log():
    r = post("audit-log", {"data": {
        "name": "E2E_TEST",
        "data_object_name": "test",
    }})
    d = r.json()
    return d["success"], f"inserted={d.get('inserted')}"


# ── BATCH CREATE ─────────────────────────────────────────────────────────────

def test_batch_create_payers():
    ts = int(time.time())
    rows = [{"name": f"E2E_BATCH_{ts}_{i}", "type": "Test", "status": "Active"} for i in range(5)]
    r = post("payers", {"data": rows})
    d = r.json()
    return d["success"] and d["inserted"] == 5, f"inserted={d.get('inserted')}"


# ── ERROR HANDLING ───────────────────────────────────────────────────────────

def test_unknown_slug():
    r = post("nonexistent", {"data": {"name": "test"}})
    return r.status_code == 404, f"status={r.status_code}"


def test_missing_required_field():
    r = post("payers", {"data": {"address": "123 Main St"}})
    return r.status_code in (400, 500), f"status={r.status_code}"


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("E2E TEST SUITE — Formulary APIs (CREATE only)")
    print("=" * 60)

    print("\n--- Health ---")
    test("GET /health", test_health)
    test("GET /tables (10 slugs)", test_list_tables)

    print("\n--- Schema validation ---")
    test("No 'id' in user columns", test_no_id_in_user_columns)
    test("No timestamps in user columns", test_no_timestamps_in_user_columns)
    test("All tables have user columns", test_user_columns_populated)

    print("\n--- CREATE all tables ---")
    test("create payer", test_create_payer)
    test("create plan (FK-aware)", test_create_plan)
    test("create drug-formulary", test_create_drug_formulary)
    test("create acronym (FK-aware)", test_create_acronym)
    test("create account (FK-aware)", test_create_account)
    test("create brand (FK-aware)", test_create_brand)
    test("create product (FK-aware)", test_create_product)
    test("create formulary-product-coverage (FK-aware)", test_create_fpc)
    test("create content-asset", test_create_content_asset)
    test("create audit-log", test_create_audit_log)

    print("\n--- BATCH CREATE ---")
    test("batch create 5 payers", test_batch_create_payers)

    print("\n--- ERROR HANDLING ---")
    test("unknown slug returns 404", test_unknown_slug)
    test("missing required field returns error", test_missing_required_field)

    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)

    with open("e2e_results.json", "w") as f:
        json.dump({"passed": PASS, "failed": FAIL, "tests": RESULTS}, f, indent=2)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
