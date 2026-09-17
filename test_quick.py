"""Quick connectivity test for all table slugs."""
import requests, time

BASE = "http://127.0.0.1:8080/api/v1/formulary"
tests = [
    ("payers", {"action": "read", "page_size": 2}),
    ("plans", {"action": "read", "page_size": 2}),
    ("drug-formulary", {"action": "read", "page_size": 2}),
    ("acronyms", {"action": "read", "page_size": 2}),
    ("accounts", {"action": "read", "page_size": 2}),
    ("brands", {"action": "read", "page_size": 2}),
    ("products", {"action": "read", "page_size": 2}),
    ("formulary-product-coverage", {"action": "read", "page_size": 2}),
    ("content-assets", {"action": "read", "page_size": 2}),
    ("audit-log", {"action": "read", "page_size": 2}),
]
for slug, body in tests:
    t = time.time()
    try:
        r = requests.post(f"{BASE}/{slug}", json=body, timeout=60)
        d = r.json()
        total = d.get("total", "?")
        elapsed = time.time() - t
        print(f"  [{r.status_code}] {slug}: total={total} ({elapsed:.1f}s)")
    except Exception as e:
        print(f"  [ERR] {slug}: {e} ({time.time()-t:.1f}s)")
