from datetime import datetime, timezone
import logging
import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from openai import OpenAI
import pytz

load_dotenv()

ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
ES_API_KEY = os.getenv('ES_API_KEY')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

logger = logging.getLogger("ray")

# @openlit.trace
def lookup_ticker_analytics_from_elastic(timestamp):
    elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    body = {
        "params": {
            "timestamp": f'{timestamp}',
            "rsi_day_gt": 30.00,
            "rsi_day_lt": 50.00,
            "macd_week_gt": 0.00,
            "macd_week_lt": 20.00
        }
    }
    results = elastic_client.search_template(id="ticker_analytics_template", body=body, index="ticker_analytics")
    all_docs = [hit['_source'] for hit in results['hits']['hits']]
    logger.info(f"Found {len(all_docs)} ticker_analytics documents in elastic search.")
    return all_docs

def log_token_count(response, model):
    elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    timestamp = datetime.now(timezone.utc).isoformat()
    doc = {"timestamp": timestamp,
           "model_id": model,
           "input_token_count": prompt_tokens,
           "output_token_count": completion_tokens
          }
    elastic_client.index(index="ticker_llm_metrics", document=doc)
    logger.debug(f"number of input tokens {prompt_tokens}")
    logger.debug(f"number of output tokens {completion_tokens}")

def utc_format_date(mm_dd_yyyy: str) -> str:
    return (pytz.timezone("America/New_York")
            .localize(datetime.strptime(mm_dd_yyyy, "%m-%d-%Y"))
            .astimezone(pytz.utc)
            .strftime("%m-%d-%Y"))

def generate_news_summary(ticker, news=None):
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
    model = "gpt-4o-mini"
    prompt = f"""1. Clean up news feed context for articles on {ticker} written in the last 3 months.
                 2. Summarize news feed context in a news summary(512 tokens or less)."""
    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "assistant", "content": f"the raw news feed data for {ticker} is: {news}"},
                {"role": "user", "content": f"news"}
            ]
        )
        logger.info(f"news summarized for ticker {ticker}")
        log_token_count(response=response, model=model)
       
        response_text = response.choices[0].message.content
        return response_text
    except Exception as e:
        logger.error(f"Exception: {e}. Failed to summarize news for ticker {ticker}")
        return f"News summarization failed for ticker {ticker}."
    
# def generate_top_tickers(top_n=20):
#     llm_client = OpenAI(api_key=OPENAI_API_KEY)
#     timestamp = utc_format_date(datetime.now(timezone.utc).strftime("%m-%d-%Y"))
#     analytics_data = lookup_ticker_analytics_from_elastic(timestamp=timestamp)
#     analyze_prompt = f"""1. Use Alexander Elder principles to recommend the top {top_n} tickers that are strong entry points based on improving technical indicators and solid fundamental data.
#                          2. Only select tickers that have a 'name', 'industry' and 'sector' field value.
#                          3. Create an integer field named 'overall_rank' from 1 to {top_n} based on a detailed review of technical data and an in-depth review of fundamental data.
#                          4. Create a field named 'technical_summary' that provides a concise summary (512 tokens or less) of the technical analysis and indicators.
#                          5. Create a field named 'fundamental_summary' that provides a concise summary (512 tokens or less) of the fundamental analysis and data.
#                          6. Ensure the final output is in JSON format, with the root element named tickers, with the fields 'ticker', 'overall_rank', 'technical_summary', 'fundamental_summary'.
#                       """
#     top_picks = []
#     model = "gpt-4o"
#     try:
#         response = llm_client.chat.completions.create(
#             model=model,
#             response_format={"type": "json_object"},
#             messages=[
#                 {"role": "system", "content": f"{analyze_prompt}"},
#                 {"role": "assistant", "content": f"Limit your analysis to the tickers and analytics data provided here: {analytics_data}"},
#                 {"role": "user", "content": f"tickers"}
#             ]
#         )
#         top_picks = json.loads(response.choices[0].message.content)
#         logger.info(f"LLM provided top {top_n} tickers by {analyze_prompt} data: {top_picks}")
#         log_token_count(response=response, model=model)
#     except Exception as e:
#         logger.error(f"Exception: {e}. Failed to provided top tickers by {analyze_prompt} for {top_n} tickers")
#         raise e
#     return top_picks