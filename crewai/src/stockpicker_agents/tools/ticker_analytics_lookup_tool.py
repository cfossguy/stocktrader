from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from elasticsearch import Elasticsearch
import os

class TickerAnalyticsLookupToolInput(BaseModel):
    """Input schema for TickerAnalyticsLookupTool."""
    ticker: str = Field(..., description="Ticker symbol of the stock.")

class TickerAnalyticsLookupTool(BaseTool):
    name: str = "TickerAnalyticsLookupTool"
    description: str = (
        "Lookup ticker analytics from elasticsearch to obtain technical data, fundamental data and news summary."
    )
    args_schema: Type[BaseModel] = TickerAnalyticsLookupToolInput

    def _run(self, ticker: str) -> str:

        ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
        ES_API_KEY = os.getenv('ES_API_KEY')
        elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
        body = {
            "query": {
                "match": {
                    "ticker": f'{ticker}'
                }
            },
            "size": 1,
            "sort": [
                {
                    "timestamp": {
                        "order": "desc"
                    }
                }
            ]
        }
        results = elastic_client.search(body=body, index="ticker_analytics")
        ticker_data = [hit['_source'] for hit in results['hits']['hits']]
        print(f"Found {len(ticker_data)} ticker_analytics documents in elastic search.")
        return ticker_data
