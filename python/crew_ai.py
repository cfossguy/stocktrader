
#!/usr/bin/env python

import sys
import os
import warnings
import datetime
import typer
from dotenv import load_dotenv
from crew import StockpickerAgents

# Ensure src is in sys.path for stockpicker_agents import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

WORKFLOW = "STOCK PICKER AGENTS"
DATE = datetime.datetime.now().strftime("%m-%d-%Y")

app = typer.Typer()
 
@app.command()
def run_crewai():
    """
    Run the crew.
    """
    inputs = {
        'workflow': WORKFLOW,
        'date': DATE
    }
    from crew import StockpickerAgents
    StockpickerAgents().crew().kickoff(inputs=inputs)

@app.command()
def train(n_iterations: int = typer.Argument(..., help="Number of iterations"), filename: str = typer.Argument(..., help="Filename")):
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'workflow': WORKFLOW,
        'date': DATE
    }
    from crew import StockpickerAgents
    try:
        StockpickerAgents().crew().train(n_iterations=n_iterations, filename=filename, inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

@app.command()
def replay(task_id: str = typer.Argument(..., help="Task ID to replay from")):
    """
    Replay the crew execution from a specific task.
    """
    from crew import StockpickerAgents
    try:
        StockpickerAgents().crew().replay(task_id=task_id)
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

@app.command()
def test(n_iterations: int = typer.Argument(..., help="Number of iterations"), openai_model_name: str = typer.Argument(..., help="OpenAI model name")):
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        'workflow': WORKFLOW,
        'date': DATE
    }
    from crew import StockpickerAgents
    try:
        StockpickerAgents().crew().test(n_iterations=n_iterations, openai_model_name=openai_model_name, inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    app()
