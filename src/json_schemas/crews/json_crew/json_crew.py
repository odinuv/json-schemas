from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.json_schemas.tools.get_configurations import GetConfigurationsTool
from src.json_schemas.tools.check_output import CheckOutputTool

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

get_configurations_tool = GetConfigurationsTool()
check_output_tool = CheckOutputTool()

@CrewBase
class JsonCrew:
    """Configuration Crew"""

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # If you would lik to add tools to your crew, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def configuration_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["configuration_analyst"],
            tools=[get_configurations_tool],
        )       
    
    @agent
    def data_sanitization_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["data_sanitization_specialist"],
        )   
    
    @agent
    def training_data_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["training_data_generator"],
        )   

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def analyze_configurations(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_configurations"],
        )

    @task
    def sanitize_configurations(self) -> Task:
        return Task(
            config=self.tasks_config["sanitize_configurations"],
        )
    
    @task
    def generate_training_data(self) -> Task:
        return Task(
            config=self.tasks_config["generate_training_data"],
            output_file='output/sample_data_{component_id}.jsonl'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Research Crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            planning=False,
            verbose=True,
            memory=False,
            # planning_llm="gpt-4o"
        )
