from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from elasticsearch import Elasticsearch
import os

class StockScreenerToolInput(BaseModel):
    """Input schema for StockScreenerToolInput."""
    rsi_day_gt: float = Field(..., description="Relative Strength Index (RSI) greater than value.", required=True)
    rsi_day_lt: float = Field(..., description="Relative Strength Index (RSI) less than value.", required=True)
    macd_week_gt: float = Field(..., description="Moving Average Convergence Divergence (MACD) greater than value.", required=True)
    macd_week_lt: float = Field(..., description="Moving Average Convergence Divergence (MACD) less than value.", required=True)

class StockScreenerTool(BaseTool):
    name: str = "StockScreenerTool"
    description: str = (
        "Obtain ticker analytics for stocks that may be a good buy opportunity."
    )
    args_schema: Type[BaseModel] = StockScreenerToolInput

    def _run(self, rsi_day_gt: float, rsi_day_lt: float, macd_week_gt: float, macd_week_lt: float) -> str:
        ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
        ES_API_KEY = os.getenv('ES_API_KEY')
        elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
        body = {
            "params": {
                "rsi_day_gt": rsi_day_gt,
                "rsi_day_lt": rsi_day_lt,
                "macd_week_gt": macd_week_gt,
                "macd_week_lt": macd_week_lt
            }
        }
        results = elastic_client.search_template(id="ticker_analytics_template", body=body, index="ticker_analytics")
        ticker_data = [hit['_source'] for hit in results['hits']['hits']]
        print(f"Found {len(ticker_data)} ticker_analytics documents in elastic search.")
        return ticker_data
