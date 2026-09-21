# Formulary Extraction APIs

FastAPI-based CREATE-only service for inserting data into 12 formulary database tables.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/PRANEETH-VEDAGIRI/formulary_apis.git
cd formulary_apis

# Create virtual environment
uv venv .venv
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

**Swagger UI:** http://localhost:8090/docs

## Database

The API connects to a local PostgreSQL database. Update `.env` with your credentials:

```
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=formulary_api_test
DB_USERNAME=postgres
DB_PASSWORD=your_password
```

### Setup Tables

Run the table creation script before first use:

```bash
python create_local_test_db.py
```

This creates 12 tables in the `crm` schema:

| Table | Slug |
|-------|------|
| `crm.payers` | `payers` |
| `crm.payer_based_plans` | `plans` |
| `crm.drug_formulary_details` | `drug-formulary` |
| `crm.acronym_details` | `acronyms` |
| `crm.accounts` | `accounts` |
| `crm.brands` | `brands` |
| `crm.product_details` | `products` |
| `crm.formulary_product_coverage` | `formulary-product-coverage` |
| `crm.content_assets` | `content-assets` |
| `crm.audit_log` | `audit-log` |
| `crm.routes_of_administration` | `routes` |
| `crm.route_mapping` | `route-mapping` |

## API Usage

### Create a Record

```
POST /api/v1/formulary/{table_slug}
```

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

**Response (single):**
```json
{
  "success": true,
  "table": "payers",
  "inserted": 1,
  "payer_id": "768848f3-42d0-4c09-af43-feb3b86223a9",
  "message": "1 row(s) created"
}
```

**Response (batch — value becomes a list):**
```json
{
  "success": true,
  "table": "routes",
  "inserted": 2,
  "route_id": ["4fad0d9f-59ea-4fe2-9362-99c4f6bfdad3", "cf4acc5d-8234-4824-8a66-5b147d46092b"],
  "message": "2 row(s) created"
}
```

Each table returns its PK under a named key:

| Slug | Response key |
|------|--------------|
| `payers` | `payer_id` |
| `plans` | `plan_id` |
| `drug-formulary` | `formulary_id` |
| `acronyms` | `acronym_id` |
| `accounts` | `account_id` |
| `brands` | `brand_id` |
| `products` | `product_id` |
| `formulary-product-coverage` | `coverage_id` |
| `content-assets` | `asset_id` |
| `audit-log` | `audit_id` |
| `routes` | `route_id` |
| `route-mapping` | `mapping_id` |

### Batch Create

```json
{
  "data": [
    {"name": "Payer A", "type": "Commercial", "status": "Active"},
    {"name": "Payer B", "type": "PPO", "status": "Active"}
  ]
}
```

### List Available Tables

```
GET /api/v1/formulary/tables
```

## Data Entry Workflow

Tables must be created in order due to foreign key dependencies:

```
1. payers          (creates payer_id)
2. plans           (needs payer_id)
3. brands          (creates brand_id)
4. routes          (creates route_id)
5. route-mapping   (needs route_id)
6. products        (needs brand_id)
7. drug-formulary  (needs brand_id + product_id)
8. formulary-product-coverage (needs payer_id + plan_id + formulary_id)
9. acronyms        (needs payer_id + member_plan_id)
10. content-assets (needs entity_id)
11. audit-log      (needs record_id)
```

Use the `ids` array from each response as the foreign key in the next table.

## Project Structure

```
formulary_apis/
  main.py              # FastAPI entry point
  config.py            # Database config
  .env                 # Credentials (not committed)
  requirements.txt     # Dependencies
  README.md
  app/
    __init__.py
    routes.py          # API endpoints
    crud.py            # INSERT engine
    schemas.py         # Pydantic models
    table_config.py    # Slug to table mapping
    database.py        # Connection pool
```

## Requirements

- Python 3.11+
- PostgreSQL 14+
- `uv` package manager
