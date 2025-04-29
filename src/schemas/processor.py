from .db import get_snowflake_connection

def get_component_ids():
    """Get unique component IDs from Snowflake based on successful jobs.
    
    Returns:
        list: List of unique component IDs that have successful jobs
    """
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    try:
        # Query to get unique component IDs with successful jobs
        query = """
        WITH latest_job AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY "kbc_component_configuration_id"
                    ORDER BY "job_start_at" DESC
                ) AS "rn"
            FROM "kbc_job"
        )
        SELECT DISTINCT "component_id", "component_listing", "component_origin" FROM (
            SELECT 
                "cc"."kbc_component_configuration_id" AS "config_id",
                SPLIT_PART("cc"."kbc_project_id", '_', 2) AS "stack_id",
                REPLACE(
                    "cc"."kbc_component_id", 
                    '_' || SPLIT_PART("cc"."kbc_project_id", '_', 2), 
                    '') 
                AS "component_id",
                "cc"."kbc_component_type" AS "component_type",
                "cc"."kbc_component_configuration" AS "config_name",
                "cc"."configuration_json" AS "config_json",
                "kc"."kbc_component_listing" AS "component_listing",
                "kc"."kbc_component_origin" AS "component_origin",
                "crw"."kbc_component_configuration_row_id" AS "row_id",
                "crw"."configuration_row_json" AS "config_row_json",
                "lj"."kbc_job_id" AS "job_id",
                "lj"."job_start_at" AS "job_start_at",
                "lj"."job_status" AS "job_status"
            FROM "kbc_component_configuration" AS "cc"
                LEFT JOIN latest_job AS "lj"
                    ON "cc"."kbc_component_configuration_id" =
                        "lj"."kbc_component_configuration_id"
                LEFT JOIN "kbc_component_configuration_row" AS "crw"
                    ON "cc"."kbc_component_configuration_id" =
                        "crw"."kbc_component_configuration_id"
                LEFT JOIN "kbc_component" AS "kc"
                    ON "cc"."kbc_component_id" = "kc"."kbc_component_id"                              
            WHERE "lj"."rn" = 1 AND
                --"kbc_configuration_is_deleted" = "true" AND
                "config_json" != '{}' AND
                "config_json" != '' AND
                "job_status" = 'success' AND
                "component_id" NOT IN (
                    'keboola.snowflake-transformation', 'keboola.python-transformation-v2', 'keboola.legacy-transformation', 
                    'keboola.synapse-transformation', 'keboola.google-bigquery-transformation', 'keboola.python-transformation',
                    'keboola.r-transformation-v2', 'keboola.no-code-dbt-transformation', 'keboola.csas-python-transformation-v2',
                    'transformation', 'keboola.oracle-transformation', 'keboola.python-snowpark-transformation', 'keboola.exasol-transformation',
                    'kds-team.app-custom-python',
                    'keboola.sandboxes', 'keboola.variables', 'keboola.data-apps', 'keboola.shared-code',
                    'keboola.runner-config-test', 'keboola.runner-workspace-bigquery-test', 
                    'keboola.runner-workspace-test', 'keboola.project-migration-tool', 'dca-custom-science-python', 'docker-demo'
                ) AND
                "component_type" NOT IN ('other', 'transformation', 'data-app') AND
                "component_id" NOT ILIKE 'keboola-test%' AND
                "stack_id" IN ('com-keboola-azure-north-europe', 'kbc-eu-central-1', 'com-keboola-gcp-europe-west3',
                    'com-keboola-gcp-us-east4', 'kbc-us-east-1'
                ) AND
                1=1
        ) AS "sub"     
        ORDER BY "component_origin" DESC, "component_listing" DESC, "component_id";
        """

        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Extract component IDs from rows
        component_ids = [row[0] for row in rows]
        
        return component_ids
                
    finally:
        cursor.close()
        conn.close() 

