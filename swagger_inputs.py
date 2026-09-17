"""
Swagger Test Inputs — paste these into Swagger UI at http://localhost:8090/docs
Each section is a ready-to-paste JSON body for POST /api/v1/formulary/{slug}
"""
import json

with open("sample_inputs.json") as f:
    data = json.load(f)

print("=" * 70)
print("SWAGGER TEST INPUTS — http://localhost:8090/docs")
print("=" * 70)
print()

for slug, info in data.items():
    print(f"{'=' * 70}")
    print(f"SLUG: {slug}")
    print(f"URL:  POST http://localhost:8090/api/v1/formulary/{slug}")
    print(f"{'=' * 70}")
    for i, rec in enumerate(info["records"], 1):
        print(f"\n--- Record {i} ---")
        print(json.dumps({"data": rec}, indent=2))
    print()

print("DONE — 5 records per table, 12 tables = 60 test inputs total")
