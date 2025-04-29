from typing import Type
import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class CheckOutputToolInput(BaseModel):
    """Input schema for CheckOutputTool."""
    jsonl_data: str = Field(..., description="The JSONl data to validate.")


class CheckOutputTool(BaseTool):
    name: str = "Check Output"
    description: str = (
        "Validates JSONl data to ensure it contains at least one row with required fields: "
        "component_id, config_example, and config_row_example. Also validates that component_id "
        "is a non-empty string and config_example is a non-empty dictionary."
    )
    args_schema: Type[BaseModel] = CheckOutputToolInput

    def _run(self, jsonl_data: str) -> str:
        if not jsonl_data.strip():
            return "Error: Empty JSONl data provided"

        # Split the JSONl data into lines and filter out empty lines and markdown code blocks
        lines = []
        for line in jsonl_data.split('\n'):
            line = line.strip()
            if line and "```" not in line and "```jsonl" not in line:
                lines.append(line)
        
        if not lines:
            return "Error: No valid JSON lines found in the data"

        # Validate each line
        for i, line in enumerate(lines, 1):
            try:
                data = json.loads(line)
                
                # Check required fields
                if not all(field in data for field in ['component_id', 'config_example', 'config_row_example']):
                    return f"Error: Line {i} is missing required fields. Must contain: component_id, config_example, config_row_example"
                
                # Validate component_id
                if not isinstance(data['component_id'], str) or not data['component_id'].strip():
                    return f"Error: Line {i} has invalid component_id. Must be a non-empty string"
                
                # Validate config_example
                if not isinstance(data['config_example'], dict) or not data['config_example']:
                    return f"Error: Line {i} has invalid config_example. Must be a non-empty dictionary"
                
            except json.JSONDecodeError:
                return f"Error: Line {i} is not valid JSON. Line: {line}"

        return "Success: All lines are valid and contain the required fields"
