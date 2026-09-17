"""Create test DB with only the 10 formulary tables needed for API testing."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

MAIN = dict(host="127.0.0.1", port=5438, dbname="medivo_qa", user="postgres", password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")
TEST_DB = "formulary_api_test"

conn = psycopg2.connect(**MAIN)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
cur.execute(f"CREATE DATABASE {TEST_DB}")
conn.close()
print(f"Created: {TEST_DB}")

conn = psycopg2.connect(host="127.0.0.1", port=5438, dbname=TEST_DB, user="postgres", password="q4$TK8((rq0e!XD9n9T.kj~_:mc$")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
cur.execute("CREATE SCHEMA IF NOT EXISTS crm")

# Only the 10 tables we need
DDL = [
    """CREATE TABLE crm.payers (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name varchar NOT NULL,
        type varchar NOT NULL,
        address varchar, city varchar, state varchar,
        zip_code varchar, country varchar, phone varchar,
        fax varchar, email varchar, website varchar,
        status varchar NOT NULL DEFAULT 'Active',
        integration_id varchar, mdm_id varchar, external_id varchar,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        formulary_url_available_flag boolean,
        source_type varchar, payer_number text,
        state_code varchar, external_id_2 varchar,
        external_id_3 varchar, external_id_4 varchar,
        external_id_5 varchar, support_start_time time,
        support_end_time time, timezone varchar,
        pa_submission_method varchar
    )""",
    """CREATE TABLE crm.payer_based_plans (
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
    """CREATE TABLE crm.drug_formulary_details (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        coverage_status varchar NOT NULL,
        drug_tier varchar,
        is_prior_authorization_required boolean NOT NULL DEFAULT false,
        is_step_therapy_required boolean NOT NULL DEFAULT false,
        is_quantity_limit_applied boolean NOT NULL DEFAULT false,
        quantity_limit_details jsonb,
        step_therapy_details jsonb,
        prior_auth_details jsonb,
        coverage_details jsonb,
        status varchar NOT NULL DEFAULT 'active',
        last_updated_date date NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        drug_name varchar,
        drug_requirements text,
        ocr_confidence_score numeric,
        llm_summary_confidence_score numeric,
        manual_review boolean NOT NULL DEFAULT false,
        source_file_hash char,
        preferred_status varchar, exclusions text,
        age_gender_restrictions text,
        diagnosis_indications_restrictions text,
        brand_id uuid, product_id uuid,
        expanded_drug_name text,
        expansion_status varchar NOT NULL DEFAULT 'Not Started'
    )""",
    """CREATE TABLE crm.acronym_details (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        state varchar,
        payer_id uuid NOT NULL,
        member_plan_id uuid NOT NULL,
        acronym varchar NOT NULL,
        expansion varchar,
        explanation text,
        coverage_status varchar NOT NULL DEFAULT 'Active',
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid
    )""",
    """CREATE TABLE crm.accounts (
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
    """CREATE TABLE crm.brands (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        brand_id uuid NOT NULL,
        name varchar NOT NULL,
        generic_name varchar,
        product_labeler_code varchar NOT NULL,
        manufacturer_id uuid NOT NULL,
        status varchar NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        uspi_label_content_asset_id uuid,
        ignore_flag boolean NOT NULL DEFAULT false
    )""",
    """CREATE TABLE crm.product_details (
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
    """CREATE TABLE crm.formulary_product_coverage (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        payer_id uuid NOT NULL,
        plan_id uuid NOT NULL,
        map_status varchar NOT NULL DEFAULT 'active',
        effective_date date,
        expiry_date date,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid, modified_by uuid,
        parent_id uuid,
        formulary_id uuid NOT NULL
    )""",
    """CREATE TABLE crm.content_assets (
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
    """CREATE TABLE crm.audit_log (
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

# Create trigger function for payer_number
DDL.append("""CREATE OR REPLACE FUNCTION crm.set_payer_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.payer_number IS NULL THEN
        NEW.payer_number := 'PAY-' || LPAD(NEXTVAL('crm.payer_number_seq')::text, 6, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql""")

DDL.append("""CREATE SEQUENCE IF NOT EXISTS crm.payer_number_seq START 1""")

for sql in DDL:
    try:
        cur.execute(sql)
        print(f"  OK: {sql[:60].split(chr(10))[0]}...")
    except Exception as e:
        if "already exists" not in str(e):
            print(f"  ERR: {e}")

# Create trigger
try:
    cur.execute("DROP TRIGGER IF EXISTS trg_payer_number ON crm.payers")
    cur.execute("""CREATE TRIGGER trg_payer_number
        BEFORE INSERT ON crm.payers
        FOR EACH ROW EXECUTE FUNCTION crm.set_payer_number()""")
    print("  Trigger: trg_payer_number")
except Exception as e:
    print(f"  Trigger err: {e}")

conn.close()
print("\nTest DB ready with 10 tables + trigger.")
