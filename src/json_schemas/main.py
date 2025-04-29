#!/usr/bin/env python
import json
import os
from pydantic import BaseModel
from crewai.flow import Flow, listen, start
from json_schemas.crews.json_crew.json_crew import JsonCrew
from schemas.processor import get_component_ids
from json_schemas.tools.check_output import CheckOutputTool

class SchemaState(BaseModel):
    component_ids: list[str] = []
    sample_jsons: dict[str, str] = {}

class SchemaFlow(Flow[SchemaState]):

    @start()
    def retrieve_component_ids(self):
        print("Retrieving component IDs")
        self.state.component_ids = get_component_ids()


    @listen(retrieve_component_ids)
    def generate_sample_jsons(self):
        for component_id in self.state.component_ids:
            # Check if output file already exists
            output_file = f"output/sample_data_{component_id}.jsonl"
            if os.path.exists(output_file):
                print(f"Skipping {component_id} - output file already exists")
                continue

            print(f"Generating example JSONs for component ID {component_id}")
            max_attempts = 5
            attempt = 1
            
            while attempt <= max_attempts:
                result = (
                    JsonCrew()
                    .crew()
                    .kickoff(inputs={"component_id": component_id, "number_of_samples": 10})
                )

                # Check if the result is a valid JSONl file
                print(f"Example JSONs generated (attempt {attempt}/{max_attempts})", result.raw)
                
                # Validate the generated JSONL file
                validation_result = CheckOutputTool()._run(result.raw)
                if validation_result.startswith("Success"):
                    print(f"Validation successful for {component_id}")
                    self.state.sample_jsons[component_id] = result.raw
                    break
                else:
                    print(f"Warning: Validation failed for {component_id} (attempt {attempt}/{max_attempts}): {validation_result}")
                    if attempt == max_attempts:
                        print(f"Failed to generate valid JSONL for {component_id} after {max_attempts} attempts")
                        self.state.sample_jsons[component_id] = result.raw  # Store the last attempt anyway
                    attempt += 1
            #break

    @listen(generate_sample_jsons)
    def save_schemas(self):
        print("Saving Sample JSONs")
        for component_id, sample_json in self.state.sample_jsons.items():
            # Read the JSONL file
            with open(f"output/sample_data_{component_id}.jsonl", "r") as f:
                jsonl_content = f.read()
            
            # Split into individual JSON objects, skipping code block markers
            json_objects = []
            for line in jsonl_content.splitlines():
                line = line.strip()
                if line and not (line.startswith("```jsonl") or line.startswith("```")):
                    try:
                        json_objects.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            # Start building the markdown content
            markdown_content = f"Below are samples how {component_id} can be configured\n\n"
            
            # Check if any config_row_example is non-empty
            has_row_schema = any(obj.get('config_row_example') for obj in json_objects)
            if has_row_schema:
                markdown_content += "The component configuration always consists of a configuration and configuration row, you need to create both.\n\n"
            
            # Add each example
            for i, obj in enumerate(json_objects, 1):
                markdown_content += f"Configuration Example {i}\n"
                markdown_content += "````\n"
                markdown_content += json.dumps(obj['config_example'], indent=2)
                markdown_content += "\n```\n\n"
                
                if obj.get('config_row_example'):
                    markdown_content += f"Configuration Row Example {i}\n"
                    markdown_content += "````\n"
                    markdown_content += json.dumps(obj['config_row_example'], indent=2)
                    markdown_content += "\n```\n\n"
            
            # Save the markdown file
            with open(f"output/{component_id}.md", "w") as f:
                f.write(markdown_content)


def kickoff():
    schema_flow = SchemaFlow()
    schema_flow.kickoff()


def plot():
    schema_flow = SchemaFlow()
    schema_flow.plot()


if __name__ == "__main__":
    kickoff()
