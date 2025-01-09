from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from elasticsearch import Elasticsearch
import os
import csv
import json
import pytz
from datetime import datetime
import functools
import traceback

class ReportArchiveTool(BaseTool):
    name: str = "ReportArchiveTool"
    description: str = (
        "Archive report details to elasticsearch."
    )

    def get_report(self, file_path: str) -> str:
        with open(file_path, 'r') as file:
            report = file.read()
        return report
    
    def csv_to_json(self, csv_filepath: str) -> json:
        data = []
        with open(csv_filepath, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                data.append(row)
        
        json_data = json.dumps(data, indent=4)
        return json.loads(json_data)
    
    def get_current_date(self):
        eastern = pytz.timezone('US/Eastern')
        eastern_time = datetime.now(eastern)
        return eastern_time.strftime('%m-%d-%Y')
    
    def catch_exceptions(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"{func.__name__}: {e}")
                traceback.print_exc()
        return wrapper

    @catch_exceptions
    def _run(self) -> str:
        ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
        ES_API_KEY = os.getenv('ES_API_KEY')
        elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
        technical_report = self.get_report("data/technical_report.txt")
        fundamental_report = self.get_report("data/fundamental_report.txt")
        portfolio_report = self.get_report("data/portfolio_report.txt")
        final_report = self.get_report("data/final_report.md")

        stocks_owned = self.csv_to_json("data/stocks_owned.csv")
        account_details = self.csv_to_json("data/account_details.csv")
        archive_date = self.get_current_date()

        stock_picker_agent_doc = {
            "technical_report": technical_report,
            "fundamental_report": fundamental_report,
            "portfolio_report": portfolio_report,
            "final_report": final_report,
            "stocks_owned": stocks_owned,
            "cash_position_usd": account_details[0].get("cash_position_usd"),
            "stock_position_usd": account_details[0].get("stock_position_usd"),
            "date": archive_date
        }

        response = elastic_client.index(
            index="stockpicker_agent",
            document=stock_picker_agent_doc,
            id=archive_date
        )

        if response['result'] in ['created', 'updated']:
            return "Report details archived successfully."
        else:
            raise Exception(f"Failed to archive report details. Response: {response}")
