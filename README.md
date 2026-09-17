# Formulary Extraction APIs

FastAPI-based CREATE-only APIs for inserting data into the 12 formulary tables.

---

## Quick Start

```bash
cd C:\Users\VH0000547\Downloads\formulary_extraction_apis

# 1. Create virtual environment
uv venv .venv
.venv\Scripts\activate

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Start server
python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

**Swagger UI:** http://localhost:8090/docs  
**Health Check:** http://localhost:8090/health

---

## Database

| Setting | Value |
|---------|-------|
| Host | `127.0.0.1` |
| Port | `5432` |
| Database | `formulary_api_test` |
| Schema | `crm` |
| User | `postgres` |
| Password | `Number@56` |

**12 Tables:**

| # | Table | Slug | Description |
|---|-------|------|-------------|
| 1 | `crm.payers` | `payers` | Insurance payer organizations |
| 2 | `crm.payer_based_plans` | `plans` | Plans under each payer |
| 3 | `crm.drug_formulary_details` | `drug-formulary` | Drug coverage details (DFD) |
| 4 | `crm.acronym_details` | `acronyms` | Abbreviations per payer/plan |
| 5 | `crm.accounts` | `accounts` | Manufacturer/drug maker accounts |
| 6 | `crm.brands` | `brands` | Drug brand names |
| 7 | `crm.product_details` | `products` | NDC/package details per brand |
| 8 | `crm.formulary_product_coverage` | `formulary-product-coverage` | Links payer+plan+drug-formulary |
| 9 | `crm.content_assets` | `content-assets` | PDF/file attachments |
| 10 | `crm.audit_log` | `audit-log` | Change tracking |
| 11 | `crm.routes_of_administration` | `routes` | Drug administration routes |
| 12 | `crm.route_mapping` | `route-mapping` | Maps products to routes |

---

## API Endpoint

### POST `/api/v1/formulary/{table_slug}`

**Request:**
```json
{
  "data": {
    "name": "Test Payer",
    "type": "Commercial",
    "status": "Active"
  }
}
```

**Response:**
```json
{
  "success": true,
  "table": "payers",
  "inserted": 1,
  "ids": ["768848f3-42d0-4c09-af43-feb3b86223a9"],
  "message": "1 row(s) created"
}
```

**Batch (multiple rows):**
```json
{
  "data": [
    {"name": "Payer A", "type": "Commercial", "status": "Active"},
    {"name": "Payer B", "type": "PPO", "status": "Active"}
  ]
}
```

### GET `/api/v1/formulary/tables`

Returns all available slugs and the columns the user must provide.

---

## Data Entry Workflow (Parent -> Child)

Data MUST be entered in this order because child tables reference parent IDs:

```
Step 1  payers                    (independent)
          |--- creates payer_id
          v
Step 2  plans                     (needs payer_id)
          |--- creates plan_id
          v
Step 3  brands                    (independent)
          |--- creates brand_id
          v
Step 4  routes                    (independent)
          |--- creates route_id
          v
Step 5  route-mapping             (needs route_id)
          v
Step 6  products                  (needs brand_id)
          |--- creates product_id
          v
Step 7  drug-formulary            (needs brand_id + product_id)
          |--- creates formulary_id
          v
Step 8  formulary-product-coverage (needs payer_id + plan_id + formulary_id)
          v
Step 9  acronyms                  (needs payer_id + member_plan_id)
          v
Step 10 content-assets            (needs entity_id from any parent)
          v
Step 11 audit-log                 (needs record_id from any parent)
```

### FK Relationships

| Child Table | FK Column | References |
|-------------|-----------|------------|
| `plans` | `payer_id` | `payers.id` |
| `acronyms` | `payer_id` | `payers.id` |
| `acronyms` | `member_plan_id` | `payer_based_plans.id` |
| `products` | `brand_id` | `brands.id` |
| `products` | `route_of_administration_id` | `routes_of_administration.id` |
| `route-mapping` | `route_of_administration_id` | `routes_of_administration.id` |
| `drug-formulary` | `brand_id` | `brands.id` |
| `drug-formulary` | `product_id` | `product_details.id` |
| `formulary-product-coverage` | `payer_id` | `payers.id` |
| `formulary-product-coverage` | `plan_id` | `payer_based_plans.id` |
| `formulary-product-coverage` | `formulary_id` | `drug_formulary_details.id` |

### ID Chaining Example

```
1. POST /payers  ->  ids: ["abc-123"]
                          |
2. POST /plans   ->  {"payer_id": "abc-123"}  ->  ids: ["def-456"]
                                                       |
3. POST /brands  ->  ids: ["ghi-789"]
                          |
4. POST /products -> {"brand_id": "ghi-789"}  ->  ids: ["jkl-012"]
                                                        |
5. POST /drug-formulary -> {"brand_id": "ghi-789", "product_id": "jkl-012"}
                          -> ids: ["mno-345"]

6. POST /formulary-product-coverage
   -> {"payer_id": "abc-123", "plan_id": "def-456", "formulary_id": "mno-345"}

7. POST /acronyms
   -> {"payer_id": "abc-123", "member_plan_id": "def-456"}
```

---

## Source File Hash

The `source_file_hash` field in `drug_formulary_details` links drugs back to their source PDF.

**How it works:**
1. PDF downloaded from payer's formulary URL
2. SHA-256 hash computed from raw PDF bytes
3. Stored in `payer_based_plans.file_hash_sha256`
4. Copied to `drug_formulary_details.source_file_hash` when drugs are extracted

```python
import hashlib
def calculate_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
```

**Join to find source plan:**
```sql
SELECT d.drug_name, p.name AS plan_name
FROM crm.drug_formulary_details d
JOIN crm.payer_based_plans p ON p.file_hash_sha256 = d.source_file_hash
```

---

## Test Inputs (Copy-Paste for Swagger)

### 1. Payers

```json
{
  "data": {
    "name": "Emblem Health",
    "type": "Commercial",
    "state": "New York",
    "status": "Active",
    "external_id": "000101",
    "formulary_url_available_flag": true,
    "payer_number": "PAY-105338",
    "support_start_time": "08:00:00",
    "support_end_time": "18:00:00",
    "timezone": "America/New_York"
  }
}
```

### 2. Plans (use payer_id from Step 1)

```json
{
  "data": {
    "name": "PPO DENTAL 2000",
    "payer_id": "PASTE_PAYER_ID_HERE",
    "formulary_url_available_flag": true,
    "type": "PPO",
    "plan_year": 2026,
    "status": "Active",
    "active": true,
    "source": "Data Collection"
  }
}
```

### 3. Drug Formulary

```json
{
  "data": {
    "coverage_status": "Covered with Conditions",
    "drug_tier": "Tier 1",
    "is_prior_authorization_required": false,
    "is_step_therapy_required": false,
    "is_quantity_limit_applied": true,
    "quantity_limit_details": {"details": "30 tablets/30 days"},
    "status": "inactive",
    "last_updated_date": "2026-08-27",
    "drug_name": "emtricitabine-tenofovir disoproxil fumarate tab 200-300 mg (Truvada)",
    "drug_requirements": "QL (30 tablets/30 days)",
    "ocr_confidence_score": "0.8500",
    "manual_review": false,
    "source_file_hash": "03605eeb1f2c2cd2abe21970d4abd7c4ae2d34872f19eedc6a2ec29ec8506201",
    "expansion_status": "Not Started"
  }
}
```

### 4. Acronyms (use payer_id + plan_id from Steps 1 & 2)

```json
{
  "data": {
    "state": "California",
    "payer_id": "PASTE_PAYER_ID_HERE",
    "member_plan_id": "PASTE_PLAN_ID_HERE",
    "acronym": "OTC",
    "expansion": "Over the Counter",
    "explanation": "Over the counter medications that do not require a prescription.",
    "coverage_status": "Covered with Conditions"
  }
}
```

### 5. Accounts

```json
{
  "data": {
    "name": "Carte Blanche Beauty, Inc.",
    "type": "MAH",
    "status": "Active",
    "organization_id": "00000000-0000-4000-8000-000000000001"
  }
}
```

### 6. Brands

```json
{
  "data": {
    "brand_id": "cf0f0b0e-5ab8-4c50-a654-bc2916763dfc",
    "name": "WELLBUTRIN XL",
    "generic_name": "bupropion hydrochloride",
    "product_labeler_code": "0187",
    "manufacturer_id": "8fd3fddc-84fb-4eb6-84f2-051e175e4c1c",
    "status": "Active",
    "ignore_flag": false
  }
}
```

### 7. Products (use brand_id from Step 3)

```json
{
  "data": {
    "brand_id": "PASTE_BRAND_ID_HERE",
    "product_ndc": "0002-6120",
    "product_id": "0002-6120_7481a510-805c-4f99-b6ae-7b44e70f5f55",
    "dosage_form_name": "TABLET, COATED",
    "route_of_administration_id": "PASTE_ROUTE_ID_HERE",
    "start_marketing_date": "2024-04-10",
    "marketing_category_name": "NDA",
    "application_number": "NDA218160",
    "ndc_exclude_flag": false,
    "ndc_package_code": "0002-6120-60",
    "package_description": "60 TABLET, COATED in 1 BOTTLE",
    "active": true,
    "dosage_strength": "120",
    "dosage_strength_unit": "mg/1",
    "substance_name": "SELPERCATINIB",
    "ignore_flag": false
  }
}
```

### 8. Formulary Product Coverage (use payer_id + plan_id + formulary_id)

```json
{
  "data": {
    "payer_id": "PASTE_PAYER_ID_HERE",
    "plan_id": "PASTE_PLAN_ID_HERE",
    "map_status": "active",
    "effective_date": "2026-08-27",
    "formulary_id": "PASTE_DFD_ID_HERE"
  }
}
```

### 9. Content Assets

```json
{
  "data": {
    "entity_type": "payer_based_plans",
    "entity_id": "PASTE_PLAN_ID_HERE",
    "original_filename": "basic-mt-2026.pdf",
    "storage_key": "mt/documents/rx-drugs/drug-lists/basic-mt-2026.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 0,
    "storage_provider": "s3",
    "active": true
  }
}
```

### 10. Audit Log

```json
{
  "data": {
    "name": "AUD-0000039749",
    "old_value": "Walmart, Inc.",
    "data_object_name": "accounts",
    "field_name": "name",
    "record_id": "PASTE_RECORD_ID_HERE",
    "operation_type": "DELETE"
  }
}
```

### 11. Routes

```json
{
  "data": {
    "name": "Infiltration",
    "definition": "Administration that results in substances passing into tissue spaces or into cells.",
    "short_name": "INFIL",
    "fda_code": "361",
    "nci_concept_id": "C38215"
  }
}
```

### 12. Route Mapping (use route_id from Step 4)

```json
{
  "data": {
    "mapping_id": "c300646c-5830-45ab-b71d-e21e2e1d101b",
    "route_of_administration_id": "PASTE_ROUTE_ID_HERE"
  }
}
```

---

## Running Tests

```bash
# Run E2E test suite (18 tests)
python test_e2e.py
```

All 18 tests must pass before deploying.

---

## Project Structure

```
formulary_extraction_apis/
  main.py                      # FastAPI entry point
  config.py                    # DB config loader
  .env                         # DB credentials
  requirements.txt             # Dependencies
  test_e2e.py                  # E2E test suite
  app/
    routes.py                  # POST endpoint
    crud.py                    # INSERT engine (returns IDs)
    schemas.py                 # Pydantic models
    table_config.py            # Slug -> table mapping
    database.py                # Connection pool
  sample_inputs.json           # 5 real records per table from main DB
  create_local_test_db.py      # Creates test DB on local PG
  insert_workflow.py           # Bulk inserts following FK order
  swagger_inputs.py            # Prints Swagger-ready JSON
```

---

## Environment Variables (.env)

```
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=formulary_api_test
DB_USERNAME=postgres
DB_PASSWORD=Number@56
```

To switch to main DB: change `DB_PORT` to `5438` and `DB_DATABASE` to `medivo_qa`.

---

## pgAdmin Setup

1. Right-click **Servers** -> **Register** -> **Server**
2. **General** tab -> Name: `Local_Test_DB`
3. **Connection** tab:
   - Host: `127.0.0.1`
   - Port: `5432`
   - Database: `formulary_api_test`
   - Username: `postgres`
   - Password: `Number@56`
4. Browse: `formulary_api_test` -> `Schemas` -> `crm` -> `Tables`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8080/8090 in use | `netstat -ano \| findstr 8090` then `taskkill /PID <pid> /F` |
| Swagger blank page | Check if CDN is blocked; try `http://localhost:8090/docs` |
| FK violation error | Ensure parent record created first, use returned ID |
| `source_file_hash` too long | Column is `varchar(256)` — hashes are 64 chars, should fit |
| Connection refused | Check `.env` matches your PG setup |
| Test DB missing tables | Run `python create_local_test_db.py` |
