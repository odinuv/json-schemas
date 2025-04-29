from typing import Type, Dict, Any
import json
from datetime import datetime

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from src.schemas.db import get_snowflake_connection


class GetConfigurationsToolInput(BaseModel):
    """Input schema for GetConfigurationsTool."""

    component_id: str = Field(..., description="The component ID to get configurations for.")
    skip_config_ids: list[str] = Field(default=[], description="List of configuration IDs to skip from the result.")


class GetConfigurationsTool(BaseTool):
    name: str = "Get Configurations"
    description: str = (
        "Get all configurations from the data directory."
    )
    args_schema: Type[BaseModel] = GetConfigurationsToolInput

    def _run(self, component_id: str, skip_config_ids: list[str] = []) -> str:
        # Validate component_id
        if not isinstance(component_id, str) or not component_id.strip():
            return "Error: component_id must be a non-empty string"

        base_query = """
        WITH latest_job AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY "kbc_component_configuration_id"
                    ORDER BY "job_start_at" DESC
                ) AS "rn"
            FROM "kbc_job"
        )
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
            "config_json" != '{}' AND
            "config_json" != '' AND
            "job_status" = 'success' AND
            "stack_id" IN ('com-keboola-azure-north-europe', 'kbc-eu-central-1', 'com-keboola-gcp-europe-west3',
                'com-keboola-gcp-us-east4', 'kbc-us-east-1'
            ) AND
            "component_id" = %s
        """

        try:
            # Get Snowflake connection
            conn = get_snowflake_connection()
            cursor = conn.cursor()
            
            # Build the query and parameters
            params = [component_id]
            if skip_config_ids:
                query = base_query + "AND \"cc\".\"kbc_component_configuration_id\" NOT IN %s\nORDER BY \"job_start_at\" DESC;"
                params.append(tuple(skip_config_ids))
            else:
                query = base_query + "ORDER BY \"job_start_at\" DESC;"
            
            # Execute query with the appropriate parameters
            cursor.execute(query, tuple(params))
            
            # Fetch all results
            results = cursor.fetchall()
            
            if not results:
                return f"No configurations found for component: {component_id}"
            
            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            
            # Process results into a structured format
            configs = []
            max_size = 100000  # Maximum allowed JSON size
            
            for row in results:
                # Create dictionary using column names as keys
                config = dict(zip(columns, row))
                result = {}
                
                # Convert JSON strings to Python dictionaries
                if config['config_json']:
                    result['config_json'] = json.loads(config['config_json'])
                else:
                    result['config_json'] = {}
                    
                if config['config_row_json']:
                    result['config_row_json'] = json.loads(config['config_row_json'])
                else:
                    result['config_row_json'] = {}
                
                # Format datetime to ISO format
                if config['job_start_at']:
                    # The timestamp is already in ISO format with timezone
                    # Just ensure it's properly formatted
                    result['job_start_at'] = config['job_start_at'].replace('Z', '+00:00')
                
                # Add the new config and check the size
                configs.append(result)
                current_json = json.dumps(configs, indent=2)
                
                # If we exceed the size limit, remove the last added config and break
                if len(current_json) > max_size:
                    configs.pop()  # Remove the last added config
                    break
            
            return json.dumps(configs, indent=2)
            
        except Exception as e:
            return f"Error fetching configurations: {str(e)}"
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
