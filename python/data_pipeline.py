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
import logging
from retrying import retry
import shutil
import typer
import functools
import subprocess
import os
import sys

load_dotenv()

use_small_dataset = False

app = typer.Typer()

ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
ES_API_KEY = os.getenv('ES_API_KEY')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YAHOO_FINANCE_CACHE_DIR = os.getenv('YAHOO_FINANCE_CACHE_DIR')
LOCAL_DATA_DIR = os.getenv('LOCAL_DATA_DIR')

if None in [ELASTIC_SEARCH_URL, ES_API_KEY, POLYGON_API_KEY, OPENAI_API_KEY]:
    raise ValueError("One or more environment variables are not set. Please check your .env file.")

def logging_setup_func():
    logger = logging.getLogger("ray")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s -- %(message)s')
    stream_handler = logging.StreamHandler(stream=sys.stdout)  # Use sys.stdout instead of default sys.stderr
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = True

logger = logging.getLogger("ray")
logging_setup_func()

def catch_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__}: {e}")
    return wrapper

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
        logger.debug(f"Cache directory does not exist: {YAHOO_FINANCE_CACHE_DIR}")

def add_stock_record(stocks_frame, ticker, name, sector, industry, category):
    new_record = pd.DataFrame([{
        'ticker': ticker,
        'name': name,
        'sector': sector,
        'industry': industry,
        'category': category
    }])
    stocks_frame = pd.concat([stocks_frame, new_record], ignore_index=True)
    logger.debug(f"Added new stock record: {new_record.to_dict(orient='records')[0]}")
    return stocks_frame

def add_etf_list(stocks_frame):
    # add ETFs that should be included in the list
    category = 'ETF'
    stocks_frame = add_stock_record(stocks_frame, 'VIX', 'CBOE Market Volitility', 'VIX', 'VIX', category)
    stocks_frame = add_stock_record(stocks_frame, 'JPST', 'JPMorgan Ultra-Short Income ETF', 'Bond Fund', 'Conservative', category)
    stocks_frame = add_stock_record(stocks_frame, 'QQQ', 'Tech Sector ETF', 'Technology', 'Technology', category)
    stocks_frame = add_stock_record(stocks_frame, 'SPY', 'SP500 ETF', 'SP500', 'SP500', category)
    stocks_frame = add_stock_record(stocks_frame, 'IWM', 'iShares Russell 2000 ETF', 'Broad Market', 'Moderate Risk', category)

    return stocks_frame

def fetch_sp500_list():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    content = response.content
    tables = pd.read_html(content)
    
    # The S&P 500 component stocks table is the second table (index 1)
    stocks_frame = tables[1]
    
    # Rename columns to match expected schema
    stocks_frame = stocks_frame.rename(columns={
        'Symbol': 'ticker', 
        'Security': 'name', 
        'GICS Sector': 'sector', 
        'GICS Sub-Industry': 'industry'
    })
    
    # Drop columns we don't need
    columns_to_drop = []
    for col in ['Founded', 'Headquarters Location', 'Date added', 'CIK']:
        if col in stocks_frame.columns:
            columns_to_drop.append(col)
    
    if columns_to_drop:
        stocks_frame = stocks_frame.drop(columns=columns_to_drop)
    
    # Keep only the columns we need
    required_columns = ['ticker', 'name', 'sector', 'industry']
    stocks_frame = stocks_frame[required_columns]

    logger.info(f"S&P 500 list fetched from Wikipedia - {len(stocks_frame)} stocks")

    if use_small_dataset:
        stocks_frame = stocks_frame.head(3)

    stocks_frame['category'] = 'SP500'
    return stocks_frame
    
@ray.remote
def get_triple_screen_median_remote(ticker, indicator, timespan):
    return market_analytics.get_triple_screen_median(ticker=ticker, indicator=indicator, timespan=timespan)

@ray.remote
def get_beta_remote(ticker):
    return market_analytics.get_beta(ticker)

@ray.remote
def get_ratios_remote(ticker):
    return market_analytics.get_ratios(ticker)

@ray.remote
def get_news_remote(ticker):
    return market_analytics.get_news(ticker)

@ray.remote
def get_balance_sheets_remote(ticker):
    return market_analytics.get_balance_sheets(ticker)

@ray.remote
def generate_fundamentals_summary_and_rank_remote(ticker, ratios, balance_sheets):
    return llm.generate_fundamentals_summary_and_rank(ticker, ratios, balance_sheets)

@ray.remote
def generate_news_summary_and_rank_remote(ticker, news):
    return llm.generate_news_summary_and_rank(ticker, news)

@ray.remote(num_cpus=12)
def generate_analytics_json_etf():
    data_dir = LOCAL_DATA_DIR
    ticker_analytics_datafile = f'{data_dir}/ticker_analytics.jsonl'
    stocks_frame = None
    try:
        stocks_frame = add_etf_list(stocks_frame)
    except Exception as e:
        logger.error("An exception occurred web scraping from wikipedia", exc_info=True)
        return None
    
    try:
        logger.info("Adding columns from yahoo finance service")
        beta_futures = stocks_frame.apply(lambda row: get_beta_remote.remote(row.ticker.strip()), axis=1).tolist()
        stocks_frame['beta'] = ray.get(beta_futures)
    except Exception as e:
        logger.error("An exception occurred getting beta from yahoo for", exc_info=True)

    try:
        logger.info("Adding technical columns from polygon service - RSI, MACD, SMA")
        rsi_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "hour"), axis=1).tolist()
        stocks_frame['rsi_hour'] = ray.get(rsi_hour_futures)

        rsi_day_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "day"), axis=1).tolist()
        stocks_frame['rsi_day'] = ray.get(rsi_day_futures)

        rsi_week_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "week"), axis=1).tolist()
        stocks_frame['rsi_week'] = ray.get(rsi_week_futures)

        stocks_frame['rsi_rank'] = stocks_frame.apply(lambda row: market_analytics.get_rsi_rank(row['rsi_hour'], row['rsi_day'], row['rsi_week']), axis=1)
        
        macd_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "hour"), axis=1).tolist()
        stocks_frame['macd_hour'] = ray.get(macd_hour_futures)

        macd_day_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "day"), axis=1).tolist()
        stocks_frame['macd_day'] = ray.get(macd_day_futures)

        macd_week_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "week"), axis=1).tolist()
        stocks_frame['macd_week'] = ray.get(macd_week_futures)

        stocks_frame['macd_rank'] = stocks_frame.apply(lambda row: market_analytics.get_macd_rank(row['macd_hour'], row['macd_day'], row['macd_week']), axis=1)

        sma_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "sma", "hour"), axis=1).tolist()
        stocks_frame['sma_hour'] = ray.get(sma_hour_futures)

        logger.info("polygon service columns added technical columns from polygon service - RSI, MACD, SMA for all tickers")
    except:
        logger.error("An exception occurred processing polygon data", exc_info=True)

    try:
        logger.info("Adding GPT-4 news summaries and ranks")
        news_summary_and_rank_futures = stocks_frame.apply(
            lambda row: generate_news_summary_and_rank_remote.remote(
                ticker=row.ticker.strip(), 
                news=get_news_remote.remote(ticker=row.ticker.strip())
            ), 
            axis=1
        ).tolist()

        news_summary_and_rank_results = ray.get(news_summary_and_rank_futures)

        # Extract 'summary' and add to the DataFrame
        stocks_frame['news_summary'] = [result['summary'] for result in news_summary_and_rank_results]

        # Add 'news_rank' only if the result is not None
        stocks_frame['news_rank'] = [result['rank'] if result['rank'] is not None else None for result in news_summary_and_rank_results]

        logger.info("GPT-4 news summaries and ranks added for all tickers")
    except Exception as e: 
        logger.error("An exception occurred generating news sentiment", exc_info=True)

    try:
        stocks_frame.to_json(ticker_analytics_datafile, orient='records', lines=True, mode='a')
    except:
        logger.error("An exception occurred writing data to jsonl", exc_info=True)


@ray.remote(num_cpus=12)
def generate_analytics_json_sp500():
    data_dir = LOCAL_DATA_DIR
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
    except Exception as e:
        logger.error("An exception occurred getting beta from yahoo for", exc_info=True)

    try:
        # fundamentals
        ratios_futures = stocks_frame.apply(lambda row: get_ratios_remote.remote(row.ticker.strip()), axis=1).tolist()
        ratios_results = ray.get(ratios_futures)

        # List of columns to add from ratios
        ratio_keys = [
            "price", "average_volume", "market_cap", "earnings_per_share", "price_to_earnings", "price_to_book", "price_to_sales", "price_to_cash_flow", "price_to_free_cash_flow", "dividend_yield", "return_on_assets", "return_on_equity", "debt_to_equity", "current", "quick", "cash", "ev_to_sales", "ev_to_ebitda", "enterprise_value", "free_cash_flow"
        ]
        # Add each column to stocks_frame
        for key in ratio_keys:
            stocks_frame[key] = [r.get(key) if r else None for r in ratios_results]

        logger.info("ratios columns added for all tickers")
    except Exception as e:
        logger.error("An exception occurred getting ratios from polygon", exc_info=True)

    try:
        logger.info("Adding technical columns from polygon service - RSI, MACD, SMA")
        rsi_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "hour"), axis=1).tolist()
        stocks_frame['rsi_hour'] = ray.get(rsi_hour_futures)

        rsi_day_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "day"), axis=1).tolist()
        stocks_frame['rsi_day'] = ray.get(rsi_day_futures)

        rsi_week_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "rsi", "week"), axis=1).tolist()
        stocks_frame['rsi_week'] = ray.get(rsi_week_futures)

        stocks_frame['rsi_rank'] = stocks_frame.apply(lambda row: market_analytics.get_rsi_rank(row['rsi_hour'], row['rsi_day'], row['rsi_week']), axis=1)
        
        macd_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "hour"), axis=1).tolist()
        stocks_frame['macd_hour'] = ray.get(macd_hour_futures)

        macd_day_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "day"), axis=1).tolist()
        stocks_frame['macd_day'] = ray.get(macd_day_futures)

        macd_week_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "macd", "week"), axis=1).tolist()
        stocks_frame['macd_week'] = ray.get(macd_week_futures)

        stocks_frame['macd_rank'] = stocks_frame.apply(lambda row: market_analytics.get_macd_rank(row['macd_hour'], row['macd_day'], row['macd_week']), axis=1)

        sma_hour_futures = stocks_frame.apply(lambda row: get_triple_screen_median_remote.remote(row.ticker.strip(), "sma", "hour"), axis=1).tolist()
        stocks_frame['sma_hour'] = ray.get(sma_hour_futures)

        logger.info("polygon service columns added technical columns from polygon service - RSI, MACD, SMA for all tickers")
    except:
        logger.error("An exception occurred processing polygon data", exc_info=True)

    try:
        logger.info("Adding GPT-4 news summaries and ranks")
        news_summary_and_rank_futures = stocks_frame.apply(
            lambda row: generate_news_summary_and_rank_remote.remote(
                ticker=row.ticker.strip(), 
                news=get_news_remote.remote(ticker=row.ticker.strip())
            ), 
            axis=1
        ).tolist()

        news_summary_and_rank_results = ray.get(news_summary_and_rank_futures)

        # Extract 'summary' and add to the DataFrame
        stocks_frame['news_summary'] = [result['summary'] for result in news_summary_and_rank_results]

        # Add 'news_rank' only if the result is not None
        stocks_frame['news_rank'] = [result['rank'] if result['rank'] is not None else None for result in news_summary_and_rank_results]

        logger.info("GPT-4 news summaries and ranks added for all tickers")
    except Exception as e: 
        logger.error("An exception occurred generating news sentiment", exc_info=True)

    try:
        logger.info("Adding GPT-4 fundamentals summaries and ranks")
        fundamentals_summary_and_rank_futures = stocks_frame.apply(
            lambda row: generate_fundamentals_summary_and_rank_remote.remote(
                ticker=row.ticker.strip(), 
                balance_sheets=get_balance_sheets_remote.remote(ticker=row.ticker.strip()),
                ratios=get_ratios_remote.remote(ticker=row.ticker.strip())
            ), 
            axis=1
        ).tolist()

        fundamentals_summary_and_rank_results = ray.get(fundamentals_summary_and_rank_futures)

        # Extract 'summary' and 'rank' from the results and add them to the DataFrame
        stocks_frame['fundamentals_summary'] = [result['summary'] for result in fundamentals_summary_and_rank_results]

        # Add 'fundamentals_rank' only if the result is not None
        stocks_frame['fundamentals_rank'] = [result['rank'] if result['rank'] is not None else None for result in fundamentals_summary_and_rank_results]

        logger.info("GPT-4 fundamentals summaries and ranks added for all tickers")
    except Exception as e: 
        logger.error("An exception occurred generating fundamentals sentiment", exc_info=True)

    try:
        stocks_frame.to_json(ticker_analytics_datafile, orient='records', lines=True, mode='a')
    except:
        logger.error("An exception occurred writing data to jsonl", exc_info=True)

def insert_jsonl_to_elastic(index_name: str):
    elastic_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    data_dir = LOCAL_DATA_DIR
    files = glob.glob(f'{data_dir}/{index_name}.jsonl')
    for file in files:
        records = []
        timestamp = datetime.now().strftime("%m-%d-%Y")
        with open(file, 'r') as f:
            for index, line in enumerate(f):
                doc = json.loads(line)
                doc['timestamp'] = timestamp
                id = f"{doc['ticker']}_{timestamp}"
                record = {
                    "_index": index_name,
                    "_source": doc,
                    "_id": id
                }
                records.append(record)
        try:
            logger.debug(f"Indexing {len(records)} documents from {file} to ElasticSearch")
            helpers.bulk(elastic_client, records, chunk_size=500)
        except helpers.BulkIndexError as e:
            logger.error(f"Failed to index documents: {e.errors}")
        logger.info(f"Successfully indexed {len(records)} documents to ElasticSearch index: {index_name}") 

@app.command()
def clear_cache():
    clear_yfinance_cache()
    # Delete ticker_analytics_datafile after clearing yfinance cache
    data_dir = os.getenv('LOCAL_DATA_DIR')
    ticker_analytics_datafile = f'{data_dir}/ticker_analytics.jsonl'
    if os.path.exists(ticker_analytics_datafile):
        try:
            os.remove(ticker_analytics_datafile)
            logger.info(f"Deleted data file: {ticker_analytics_datafile}")
        except Exception as e:
            logger.error(f"Failed to delete data file: {ticker_analytics_datafile}", exc_info=True)
    else:
        logger.info(f"Data file does not exist: {ticker_analytics_datafile}")
    
@app.command()
def test():
    fetch_sp500_list()

@app.command()
def elastic_bulk_load():
    insert_jsonl_to_elastic("ticker_analytics")

@app.command()
@catch_exceptions
def start_ray():
    command = ["ray", "start", "--head", "--dashboard-port=8080"]
    env = os.environ.copy()
    env["RAY_DISABLE_TPU_DETECTION"] = "1"
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode == 0:
        logger.info("RAY: started successfully")
    else:
        logger.info("RAY: failed to start. It's probably already running or a permissions issue.")

@app.command()
@catch_exceptions
def stop_ray():
    command = ["ray", "stop"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        logger.info("RAY: stopped successfully")
        logger.info(result.stdout)
    else:
        logger.info("RAY: failed to stop")
        logger.info(result.stderr)

@app.command()
def run_data_pipeline():
    start_ray()
    ray.init(address='auto', ignore_reinit_error=True, runtime_env={"env_vars": {
        "ELASTIC_SEARCH_URL": ELASTIC_SEARCH_URL,
        "ES_API_KEY": ES_API_KEY,
        "POLYGON_API_KEY": POLYGON_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY
    },"worker_process_setup_hook": logging_setup_func},
    log_to_driver=True)
    
    clear_cache()

    ray.get(generate_analytics_json_sp500.remote())
    ray.get(generate_analytics_json_etf.remote())
    insert_jsonl_to_elastic("ticker_analytics")
    stop_ray()
    
@app.command()
def test_logging():
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.error("This is an error message")
    
if __name__ == "__main__":
    app()
