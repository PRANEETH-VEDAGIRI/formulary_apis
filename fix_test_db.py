"""Fix tables that failed due to uuid_generate_v4."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

TEST_DB = "formulary_api_test"
conn = psycopg2.connect(host="127.0.0.1", port=5438, dbname=TEST_DB, user="postgres", password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

DDL = [
    """CREATE TABLE IF NOT EXISTS crm.payer_based_plans (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name varchar NOT NULL,
        payer_id uuid NOT NULL,
        formulary_url_available_flag boolean NOT NULL DEFAULT true,
        type varchar NOT NULL,
        sub_type varchar, bin_number varchar,
        pcn_number varchar, group_number varchar,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        direct_formulary_url varchar, url_status varchar,
        plan_year smallint NOT NULL,
        ingest_status varchar, ingest_completed_at timestamptz,
        file_hash_sha256 char, run varchar,
        status varchar NOT NULL DEFAULT 'Active',
        active boolean NOT NULL DEFAULT true,
        source varchar NOT NULL DEFAULT 'Data Collection'
    )""",
    """CREATE TABLE IF NOT EXISTS crm.accounts (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name varchar NOT NULL,
        type varchar NOT NULL,
        site varchar, address varchar, city varchar,
        state varchar, zip_code varchar, country varchar,
        phone varchar, fax varchar, email varchar,
        website varchar, npi varchar, tax_id varchar,
        status varchar NOT NULL DEFAULT 'Draft',
        owner_id uuid, integration_id varchar,
        mdm_id varchar, external_id varchar,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        state_code varchar, signup_link varchar,
        email_domain varchar, organization_id uuid NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS crm.product_details (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        brand_id uuid NOT NULL,
        product_ndc varchar NOT NULL,
        product_id varchar NOT NULL,
        dosage_form_name varchar,
        route_of_administration_id uuid,
        start_marketing_date date,
        end_marketing_date date,
        marketing_category_name varchar,
        application_number varchar,
        ndc_exclude_flag boolean NOT NULL DEFAULT false,
        ndc_package_code varchar,
        package_description varchar,
        active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        dosage_strength varchar, dosage_strength_unit varchar,
        substance_name varchar, pipeline_action_note text,
        ignore_flag boolean NOT NULL DEFAULT false,
        dosage_unit varchar
    )""",
    """CREATE TABLE IF NOT EXISTS crm.content_assets (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        entity_type varchar NOT NULL,
        entity_id uuid,
        original_filename varchar NOT NULL,
        storage_key varchar NOT NULL,
        mime_type varchar,
        size_bytes bigint NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid,
        storage_provider varchar NOT NULL DEFAULT 'local',
        content_type varchar, content_template_id uuid,
        active boolean NOT NULL DEFAULT true,
        organization_id uuid,
        processing_status varchar,
        external_job_ref varchar, error_message text
    )""",
    """CREATE TABLE IF NOT EXISTS crm.audit_log (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name varchar NOT NULL,
        old_value varchar, new_value varchar,
        data_object_name varchar NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        modified_by uuid,
        field_name varchar, record_id uuid,
        operation_type varchar, request_id varchar,
        transaction_id varchar
    )""",
]

for sql in DDL:
    try:
        cur.execute(sql)
        print(f"  OK: {sql.split(chr(10))[0][:60]}")
    except Exception as e:
        print(f"  ERR: {e}")

# Verify all 10 tables exist
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='crm' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print(f"\nTables in test DB: {tables}")

conn.close()
