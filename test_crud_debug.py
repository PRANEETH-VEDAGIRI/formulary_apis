import requests
BASE = "http://127.0.0.1:8080/api/v1/formulary/payers"
for name in ["E2E_TEST_PAYER_DELETE_ME", "E2E_TEST_PAYER_UPDATE_ME", "E2E_TEST_DEBUG"]:
    r = requests.post(BASE, json={"action": "delete", "filters": {"name": name}}, timeout=10)
    d = r.json()
    print(f"  cleanup {name}: {d.get('total', 0)} deleted")

# Now test CRUD fresh
print("\n--- CRUD test ---")
r = requests.post(BASE, json={"action": "create", "data": {"name": "E2E_TEST_FRESH", "type": "Test", "state": "TEST", "status": "Active"}}, timeout=10)
print(f"create: {r.json()}")
r2 = requests.post(BASE, json={"action": "read", "filters": {"name": "E2E_TEST_FRESH"}}, timeout=10)
print(f"read: total={r2.json()['total']}, data={len(r2.json()['data'])} rows")
r3 = requests.post(BASE, json={"action": "update", "filters": {"name": "E2E_TEST_FRESH"}, "update_fields": {"state": "UPDATED"}}, timeout=10)
print(f"update: {r3.json()}")
r4 = requests.post(BASE, json={"action": "delete", "filters": {"name": "E2E_TEST_FRESH"}}, timeout=10)
print(f"delete: {r4.json()}")
