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
        LOCAL_DATA_DIR = os.getenv('LOCAL_DATA_DIR')
        elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY, request_timeout=120)

        def data_path(filename):
            return os.path.join(LOCAL_DATA_DIR, filename)

        screen_report = self.get_report(data_path("screen_report.md"))
        technical_report = self.get_report(data_path("technical_report.md"))
        fundamental_report = self.get_report(data_path("fundamental_report.md"))
        portfolio_report = self.get_report(data_path("portfolio_report.md"))
        final_report = self.get_report(data_path("final_report.md"))
        etf_report = self.get_report(data_path("etf_report.md"))

        stocks_owned = self.csv_to_json(data_path("stocks_owned.csv"))
        account_details = self.csv_to_json(data_path("account_details.csv"))
        archive_date = self.get_current_date()

        print(f"Archiving report details for {archive_date}...")

        stock_position_usd = 0
        cash_position_usd = 0
        for acct in account_details:
            cash_position_usd = cash_position_usd + float(acct["cash_position_usd"])
            stock_position_usd = stock_position_usd + float(acct["stock_position_usd"])
        account_balance = cash_position_usd + stock_position_usd

        stock_picker_agent_doc = {
            "screen_report": screen_report,
            "technical_report": technical_report,
            "fundamental_report": fundamental_report,
            "portfolio_report": portfolio_report,
            "final_report": final_report,
            "etf_report": etf_report,
            "stocks_owned": stocks_owned,
            "account_details": account_details,
            "cash_position_usd": cash_position_usd,
            "stock_position_usd": stock_position_usd,
            "account_balance": account_balance,
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
