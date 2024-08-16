import pandas as pd
from pandarallel import pandarallel
import time
from datetime import datetime
import json
import requests
from elasticsearch import helpers
import market_analytics 
import llm
import glob
from setup_environment import logger, elastic_client
import typer
import pytz
import re

use_small_dataset = False

formatted_date = datetime.now().strftime("%m-%d-%Y")

data_dir = './data'
ticker_analytics_datafile = f'{data_dir}/ticker_analytics-{formatted_date}.jsonl'
ticker_watchlist_datafile = f'{data_dir}/ticker_watchlist-{formatted_date}.jsonl'
app = typer.Typer()

logger = logger("data_pipeline")
elastic_client = elastic_client()

def generate_analytics_json_sp500():
    start = time.time()
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url, verify=False)
    content = response.content
    tables = pd.read_html(content)
    stocks_frame = tables[0]  # The first table on the page is the S&P 500 list

    stocks_frame = stocks_frame.rename(columns={'Symbol': 'ticker', 'Security': 'name', 'GICS Sector': 'sector', 'GICS Sub-Industry': 'industry', 'Date added':'added_to_sp500_ts', 'CIK': 'cik'})
    stocks_frame = stocks_frame.drop(columns=['Founded','Headquarters Location', 'added_to_sp500_ts', 'cik'])
    if use_small_dataset:
        stocks_frame = stocks_frame.head(10)
   
    pandarallel.initialize(progress_bar=False)

    #technicals
    indicators = ['rsi', 'macd', 'sma']
    timespans = ['hour', 'day', 'week']
    for indicator in indicators:
        for timespan in timespans:
            stocks_frame[f'{indicator}_{timespan}'] = stocks_frame.parallel_apply(lambda row: market_analytics.get_triple_screen_median(ticker=row.ticker.strip(), indicator=indicator, timespan=timespan), axis=1)
    
    logger.info("technical columns added for all tickers")
    stocks_frame['beta'] = stocks_frame.parallel_apply(lambda row: market_analytics.get_beta(row.ticker.strip()), axis=1)
    logger.info("beta column added for all tickers")

    #fundamentals
    stocks_frame['market_cap'] = stocks_frame.parallel_apply(lambda row: market_analytics.get_market_cap(row.ticker.strip()), axis=1)
    logger.info("market_cap column added for all tickers")

    stocks_frame['dividend_yield'] = stocks_frame.parallel_apply(lambda row: market_analytics.get_dividend_yield(row.ticker.strip()), axis=1)
    logger.info("dividend_yield column added for all tickers")

    stocks_frame['pe'] = stocks_frame.parallel_apply(lambda row: market_analytics.get_pe(row.ticker.strip()), axis=1)
    logger.info("pe column added for all tickers")

    stocks_frame.to_json(ticker_analytics_datafile, orient='records', lines=True)

    end = time.time()
    logger.info(f'stock universe records loaded to jsonl in {end - start} seconds')

def generate_watchlist_json_sp500():
    tickers = llm.generate_top_tickers(top_n=20, timestamp=formatted_date)
 
    with open(ticker_watchlist_datafile, 'w') as f:
        for ticker in tickers:
            json.dump(ticker, f)
            f.write('\n')

def utc_format_date(mm_dd_yyyy: str) -> str:
    return (pytz.timezone("America/New_York")
            .localize(datetime.strptime(mm_dd_yyyy, "%m-%d-%Y"))
            .astimezone(pytz.utc)
            .strftime("%m-%d-%Y"))

def parse_date_from_filename(filename: str) -> str:
    pattern = r'\d{2}-\d{2}-\d{4}'
    match = re.search(pattern, filename)
    if match:
        return utc_format_date(match.group(0))
    else:
        raise ValueError(f"No date found in filename: {filename}")

def insert_jsonl_to_elastic(index_name: str):
    files = glob.glob(f'{data_dir}/{index_name}*.jsonl')
    for file in files:
        records = []
        with open(file, 'r') as f:
            timestamp = parse_date_from_filename(file)
            for index, line in enumerate(f):
                doc = json.loads(line)
                doc['timestamp'] = timestamp
                record = {
                    "_index": index_name,
                    "_source": doc,
                    "_id": f"{index}_{timestamp}"
                }
                records.append(record)
                
        # Use the helpers module's bulk function to insert the data
        try:
            logger.info(f"Indexing {len(records)} documents from {file} to ElasticSearch")
            helpers.bulk(elastic_client, records, chunk_size=500)
        except helpers.BulkIndexError as e:
            print(f"Failed to index documents: {e.errors}") 

@app.command()
def ticker_analytics():
    generate_analytics_json_sp500()
    
@app.command()
def ticker_analytics_to_elastic():
    insert_jsonl_to_elastic(index_name="ticker_analytics")

@app.command()
def ticker_watchlist():
    generate_watchlist_json_sp500()

@app.command()
def ticker_watchlist_to_elastic():
    insert_jsonl_to_elastic(index_name="ticker_watchlist")

@app.command()
def all():
    ticker_analytics()
    ticker_analytics_to_elastic()
    ticker_watchlist()
    ticker_watchlist_to_elastic()

if __name__ == "__main__":
    app()
    
