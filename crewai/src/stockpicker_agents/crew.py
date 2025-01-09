from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, FileReadTool
from stockpicker_agents.tools import TickerAnalyticsLookupTool, StockScreenerTool, ReportArchiveTool
import os

# If you want to run a snippet of code before or after the crew starts, 
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class StockpickerAgents():
	
	"""StockpickerAgents crew"""

	# Learn more about YAML configuration files here:
	# Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
	# Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	# Create tools
	search_tool = SerperDevTool()
	stocks_owned = FileReadTool(file_path="data/stocks_owned.csv")
	account_details = FileReadTool(file_path="data/account_details.csv")
	technical_report = FileReadTool(file_path="data/technical_report.txt")
	fundamental_report = FileReadTool(file_path="data/fundamental_report.txt")
	portfolio_report = FileReadTool(file_path="data/portfolio_report.txt")

	ticker_analytics_lookup = TickerAnalyticsLookupTool()
	stock_screener_tool = StockScreenerTool()
	report_archive_tool = ReportArchiveTool()

	@agent
	def stock_screener(self) -> Agent:
		return Agent(
			config=self.agents_config['stock_screener'],
			verbose=True,
			tools=[self.stock_screener_tool]
		)

	@agent
	def fundamental_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['fundamental_analyst'],
			verbose=True,
			tools=[self.stocks_owned, self.ticker_analytics_lookup]
		)
	
	@agent
	def technical_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['technical_analyst'],
			verbose=True,
			tools=[self.stocks_owned, self.ticker_analytics_lookup]
		)
	
	@agent
	def portfolio_manager(self) -> Agent:
		return Agent(
			config=self.agents_config['portfolio_manager'],
			verbose=True,
			tools=[self.stocks_owned, self.account_details, self.ticker_analytics_lookup, self.technical_report, self.fundamental_report]
		)
	
	@agent
	def report_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['report_analyst'],
			verbose=True,
			tools=[self.ticker_analytics_lookup, self.technical_report, self.fundamental_report, self.portfolio_report, self.report_archive_tool]
		)
	
	@task
	def stock_screen(self) -> Task:
		return Task(
			config=self.tasks_config['stock_screen']
		)

	@task
	def technical_analysis(self) -> Task:
		return Task(
			config=self.tasks_config['technical_analysis']
		)
	
	
	@task
	def fundamental_analysis(self) -> Task:
		return Task(
			config=self.tasks_config['fundamental_analysis']
		)
	
	@task
	def portfolio_adjustments(self) -> Task:
		return Task(
			config=self.tasks_config['portfolio_adjustments'],
		)
	
	@task
	def final_report_task(self) -> Task:
		return Task(
			config=self.tasks_config['final_report']
			
		)
	
	@task
	def archive_report_task(self) -> Task:
		return Task(
			config=self.tasks_config['archive_report']
			
		)
	
	@crew
	def crew(self) -> Crew:
		"""Creates the StockpickerAgents crew"""
		# To learn how to add knowledge sources to your crew, check out the documentation:
		# https://docs.crewai.com/concepts/knowledge#what-is-knowledge

		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=True,
			# process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
		)
