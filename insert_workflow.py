"""Insert sample data following the parent→child workflow order."""
import json
import requests

BASE = "http://127.0.0.1:8090/api/v1/formulary"

with open("sample_inputs.json") as f:
    data = json.load(f)

def post(slug, record):
    r = requests.post(f"{BASE}/{slug}", json={"data": record}, timeout=30)
    return r.json()

# ── STEP 1: Payers ───────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1: Payers")
print("=" * 60)
payer_ids = []
for i, rec in enumerate(data["payers"]["records"]):
    resp = post("payers", rec)
    pid = resp["ids"][0] if resp.get("ids") else None
    payer_ids.append(pid)
    print(f"  {i+1}. {rec['name']} -> {pid}")

# ── STEP 2: Plans (needs payer_id) ──────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: Plans")
print("=" * 60)
plan_ids = []
for i, rec in enumerate(data["plans"]["records"]):
    rec["payer_id"] = payer_ids[i % len(payer_ids)]
    resp = post("plans", rec)
    plid = resp["ids"][0] if resp.get("ids") else None
    plan_ids.append(plid)
    print(f"  {i+1}. {rec['name']} -> {plid}")

# ── STEP 3: Brands ───────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: Brands")
print("=" * 60)
brand_ids = []
for i, rec in enumerate(data["brands"]["records"]):
    resp = post("brands", rec)
    bid = resp["ids"][0] if resp.get("ids") else None
    brand_ids.append(bid)
    print(f"  {i+1}. {rec['name']} -> {bid}")

# ── STEP 4: Routes of Administration ─────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: Routes of Administration")
print("=" * 60)
route_ids = []
for i, rec in enumerate(data["routes"]["records"]):
    resp = post("routes", rec)
    rid = resp["ids"][0] if resp.get("ids") else None
    route_ids.append(rid)
    print(f"  {i+1}. {rec['name']} -> {rid}")

# ── STEP 5: Route Mapping (needs route_id) ──────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5: Route Mapping")
print("=" * 60)
for i, rec in enumerate(data["route-mapping"]["records"]):
    rec["route_of_administration_id"] = route_ids[i % len(route_ids)]
    resp = post("route-mapping", rec)
    print(f"  {i+1}. mapping_id={rec['mapping_id'][:8]}... -> {resp.get('ids', ['N/A'])}")

# ── STEP 6: Products (needs brand_id) ───────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6: Products")
print("=" * 60)
product_ids = []
for i, rec in enumerate(data["products"]["records"]):
    rec["brand_id"] = brand_ids[i % len(brand_ids)]
    if route_ids:
        rec["route_of_administration_id"] = route_ids[0]
    resp = post("products", rec)
    prid = resp["ids"][0] if resp.get("ids") else None
    product_ids.append(prid)
    print(f"  {i+1}. {rec.get('substance_name','?')} -> {prid}")

# ── STEP 7: Drug Formulary (needs brand_id + product_id) ────────────────────
print("\n" + "=" * 60)
print("STEP 7: Drug Formulary Details")
print("=" * 60)
formulary_ids = []
for i, rec in enumerate(data["drug-formulary"]["records"]):
    rec["brand_id"] = brand_ids[i % len(brand_ids)]
    rec["product_id"] = product_ids[i % len(product_ids)]
    resp = post("drug-formulary", rec)
    fid = resp["ids"][0] if resp.get("ids") else None
    formulary_ids.append(fid)
    print(f"  {i+1}. {rec['drug_name'][:40]}... -> {fid}")

# ── STEP 8: Formulary Product Coverage (needs payer_id + plan_id + formulary_id)
print("\n" + "=" * 60)
print("STEP 8: Formulary Product Coverage")
print("=" * 60)
for i, rec in enumerate(data["formulary-product-coverage"]["records"]):
    rec["payer_id"] = payer_ids[i % len(payer_ids)]
    rec["plan_id"] = plan_ids[i % len(plan_ids)]
    rec["formulary_id"] = formulary_ids[i % len(formulary_ids)]
    resp = post("formulary-product-coverage", rec)
    print(f"  {i+1}. payer={payer_ids[i%len(payer_ids)][:8]}... plan={plan_ids[i%len(plan_ids)][:8]}... -> {resp.get('ids', ['N/A'])}")

# ── STEP 9: Acronyms (needs payer_id + member_plan_id) ─────────────────────
print("\n" + "=" * 60)
print("STEP 9: Acronyms")
print("=" * 60)
for i, rec in enumerate(data["acronyms"]["records"]):
    rec["payer_id"] = payer_ids[i % len(payer_ids)]
    rec["member_plan_id"] = plan_ids[i % len(plan_ids)]
    resp = post("acronyms", rec)
    print(f"  {i+1}. {rec['acronym']} -> {resp.get('ids', ['N/A'])}")

# ── STEP 10: Content Assets ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 10: Content Assets")
print("=" * 60)
for i, rec in enumerate(data["content-assets"]["records"]):
    resp = post("content-assets", rec)
    print(f"  {i+1}. {rec['original_filename'][:30]}... -> {resp.get('ids', ['N/A'])}")

# ── STEP 11: Audit Log ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 11: Audit Log")
print("=" * 60)
for i, rec in enumerate(data["audit-log"]["records"]):
    resp = post("audit-log", rec)
    print(f"  {i+1}. {rec['name']} -> {resp.get('ids', ['N/A'])}")

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Payers created:          {len(payer_ids)}")
print(f"  Plans created:           {len(plan_ids)}")
print(f"  Brands created:          {len(brand_ids)}")
print(f"  Routes created:          {len(route_ids)}")
print(f"  Products created:        {len(product_ids)}")
print(f"  Drug Formularies created: {len(formulary_ids)}")
print("\nAll data inserted following parent→child workflow!")
