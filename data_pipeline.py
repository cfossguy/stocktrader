import ray
import pandas as pd
from datetime import datetime, timedelta
import json
import requests
from elasticsearch import helpers
import market_analytics 
import llm
import glob
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import os
import logging
from retrying import retry
import shutil

load_dotenv()

use_small_dataset = False

logger = logging.getLogger("ray")

ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
ES_API_KEY = os.getenv('ES_API_KEY')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YAHOO_FINANCE_CACHE_DIR = os.getenv('YAHOO_FINANCE_CACHE_DIR')

if None in [ELASTIC_SEARCH_URL, ES_API_KEY, POLYGON_API_KEY, OPENAI_API_KEY]:
    raise ValueError("One or more environment variables are not set. Please check your .env file.")

def clear_yfinance_cache():
    if os.path.exists(YAHOO_FINANCE_CACHE_DIR):
        last_modified_time = os.path.getmtime(YAHOO_FINANCE_CACHE_DIR)
        last_modified_date = datetime.fromtimestamp(last_modified_time)
        if datetime.now() - last_modified_date > timedelta(hours=24):
            shutil.rmtree(YAHOO_FINANCE_CACHE_DIR)
            logger.info(f"Cleared cache directory: {YAHOO_FINANCE_CACHE_DIR}")
        else:
            logger.info(f"Cache directory is less than 24 hours old: {YAHOO_FINANCE_CACHE_DIR}")
    else:
        logger.warning(f"Cache directory does not exist: {YAHOO_FINANCE_CACHE_DIR}")

def fetch_sp500_list():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url, verify=False)
    content = response.content
    tables = pd.read_html(content)
    stocks_frame = tables[0]  # The first table on the page is the S&P 500 list
    stocks_frame = stocks_frame.rename(columns={'Symbol': 'ticker', 'Security': 'name', 'GICS Sector': 'sector', 'GICS Sub-Industry': 'industry', 'Date added':'added_to_sp500_ts', 'CIK': 'cik'})
    stocks_frame = stocks_frame.drop(columns=['Founded','Headquarters Location', 'added_to_sp500_ts', 'cik'])
    logger.info("S&P 500 list fetched from wikipedia")

    if use_small_dataset:
        # stocks_frame = stocks_frame.head(50)
        stocks_frame = stocks_frame[stocks_frame['ticker'] == 'PGR']

    return stocks_frame

@ray.remote
def get_triple_screen_median_remote(ticker, indicator, timespan):
    return market_analytics.get_triple_screen_median(ticker=ticker, indicator=indicator, timespan=timespan)

@ray.remote
def get_beta_remote(ticker):
    return market_analytics.get_beta(ticker)

@ray.remote
def get_market_cap_remote(ticker):
   return market_analytics.get_market_cap(ticker)

@ray.remote
def get_dividend_yield_remote(ticker):
    return market_analytics.get_dividend_yield(ticker)

@ray.remote
def get_pe_remote(ticker):
    return market_analytics.get_pe(ticker=ticker)

@ray.remote
def generate_news_summary_remote(ticker, news):
    return llm.generate_news_summary(ticker, news)

@ray.remote
def get_news_remote(ticker):
    return market_analytics.get_news(ticker)

@ray.remote(num_cpus=12)
def generate_analytics_json_sp500():
    data_dir = './data'
    ticker_analytics_datafile = f'{data_dir}/ticker_analytics.jsonl'
    stocks_frame = None
    try:
        stocks_frame = fetch_sp500_list()
    except Exception as e:
        logger.error("An exception occurred web scraping from wikipedia", exc_info=True)
        return None
    
    try:
        logger.info("Adding columns from yahoo finance service")
        beta_futures = stocks_frame.apply(lambda row: get_beta_remote.remote(row.ticker.strip()), axis=1).tolist()
        stocks_frame['beta'] = ray.get(beta_futures)

        # fundamentals
        market_cap_futures = stocks_frame.apply(lambda row: get_market_cap_remote.remote(row.ticker.strip()), axis=1).tolist()
        stocks_frame['market_cap'] = ray.get(market_cap_futures)
        logger.info("market_cap column added for all tickers")

        dividend_yield_futures = stocks_frame.apply(lambda row: get_dividend_yield_remote.remote(row.ticker.strip()), axis=1).tolist()
        stocks_frame['dividend_yield'] = ray.get(dividend_yield_futures)
        logger.info("dividend_yield column added for all tickers")
        logger.info("yahoo finance service columns added for all tickers")
    except:
        logger.error("An exception occurred processing yahoo finance data", exc_info=True)

    try:
        logger.info("Adding columns from polygon service")
        rsi_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "hour"), axis=1).tolist()
        stocks_frame['rsi_hour'] = ray.get(rsi_hour_futures)

        rsi_day_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "day"), axis=1).tolist()
        stocks_frame['rsi_day'] = ray.get(rsi_day_futures)

        rsi_week_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "week"), axis=1).tolist()
        stocks_frame['rsi_week'] = ray.get(rsi_week_futures)

        macd_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "hour"), axis=1).tolist()
        stocks_frame['macd_hour'] = ray.get(macd_hour_futures)

        macd_day_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "day"), axis=1).tolist()
        stocks_frame['macd_day'] = ray.get(macd_day_futures)

        macd_week_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "week"), axis=1).tolist()
        stocks_frame['macd_week'] = ray.get(macd_week_futures)

        sma_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "sma", "hour"), axis=1).tolist()
        stocks_frame['sma_hour'] = ray.get(sma_hour_futures)

        pe_futures = stocks_frame.apply(lambda row: get_pe_remote.remote(row.ticker.strip()), axis=1).tolist()
        stocks_frame['pe'] = ray.get(pe_futures)
        logger.info("pe column added for all tickers")

        logger.info("polygon service columns added for all tickers")
    except:
        logger.error("An exception occurred processing polygon data", exc_info=True)

    try:
        logger.info("Adding GPT-4 news summaries")
        news_summary_futures = stocks_frame.apply(
            lambda row: generate_news_summary_remote.remote(
                ticker=row.ticker.strip(), 
                news=get_news_remote.remote(ticker=row.ticker.strip())
            ), 
            axis=1
        ).tolist()
        stocks_frame['news_summary'] = ray.get(news_summary_futures)
    except Exception as e: 
        logger.error("An exception occurred generating news sentiment", exc_info=True)

    try:
        stocks_frame.to_json(ticker_analytics_datafile, orient='records', lines=True)
    except:
        logger.error("An exception occurred writing data to jsonl", exc_info=True)

@ray.remote(num_cpus=12)
def insert_jsonl_to_elastic(index_name: str):
    elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    data_dir = './data'
    files = glob.glob(f'{data_dir}/{index_name}.jsonl')
    for file in files:
        records = []
        timestamp = datetime.now().strftime("%m-%d-%Y")
        with open(file, 'r') as f:
            for index, line in enumerate(f):
                doc = json.loads(line)
                doc['timestamp'] = timestamp
                record = {
                    "_index": index_name,
                    "_source": doc,
                    "_id": f"{index}_{timestamp}"
                }
                records.append(record)
        try:
            logger.info(f"Indexing {len(records)} documents from {file} to ElasticSearch")
            helpers.bulk(elastic_client, records, chunk_size=500)
        except helpers.BulkIndexError as e:
            logger.error(f"Failed to index documents: {e.errors}") 

def logging_setup_func():
    logger = logging.getLogger("ray")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s -- %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    
if __name__ == "__main__":
    
    ray.init(address='auto', runtime_env={"env_vars": {
        "ELASTIC_SEARCH_URL": ELASTIC_SEARCH_URL,
        "ES_API_KEY": ES_API_KEY,
        "POLYGON_API_KEY": POLYGON_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY
    },"worker_process_setup_hook": logging_setup_func},
    log_to_driver=True)
    
    clear_yfinance_cache()

    ray.get(generate_analytics_json_sp500.remote())
    ray.get(insert_jsonl_to_elastic.remote("ticker_analytics"))
   