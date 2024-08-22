from retrying import retry
import requests
import json
import market_analytics
from setup_environment import llm_client, elastic_client, polygon_client, logger
from datetime import datetime, timezone

llm_client = llm_client()
elastic_client = elastic_client()
polygon_client = polygon_client()
logger = logger("llm")

# Define a function to check if the exception is a request exception
def retry_if_request_exception(exception):
    logger.error(f"Exception: {exception}. Will retry after backoff period.")
    return True

# Define a retry decorator with exponential backoff
retry_decorator = retry(retry_on_exception=retry_if_request_exception,
                        stop_max_attempt_number=5,
                        wait_exponential_multiplier=1000,  # Wait 2^x * 1000 milliseconds between each retry
                        wait_exponential_max=10000)  # Maximum wait time is 10 seconds

def lookup_news_from_polygon(ticker):
    news = market_analytics.get_news(ticker=ticker)
    return news

def lookup_ticker_analytics_from_elastic(timestamp):
    # body = {
    #     "query": {
    #         "match": {
    #         "timestamp": f'{timestamp}'
    #         }
    #     },
    #     "size": 1000
    # }
    # results = elastic_client.search(index="ticker_analytics", body=body)
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

@retry_decorator
def generate_sentiment(ticker):
    news = lookup_news_from_polygon(ticker)
    model = "gpt-4o-mini"
    prompt = f"""1. Clean up news feed context for articles on {ticker} written in the last 3 months.
                 2. Summarize news feed context in a single, plain text field named 'news_summary'(512 tokens or less).
                 3. Create a field named 'news_sentiment' that provides rating value of BUY, HOLD or SELL. The scale is as follows SELL = negative, neutral or mixed. HOLD = mostly postive. BUY = all positive.
                 The final output should be in JSON format and contain the following fields: ticker, 'news_sentiment', 'news_summary'."""
    try:
        response = llm_client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "assistant", "content": f"the raw news feed data for {ticker} is: {news}"},
                {"role": "user", "content": f"news"}
            ]
        )
        logger.info(f"news summarized for ticker {ticker}")
        log_token_count(response, model)
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Exception: {e}. Failed to summarize news for ticker {ticker}")
        return "News summarization failed for ticker {ticker}."
    
@retry_decorator
def generate_top_tickers(top_n=20, timestamp=None):
    
    analytics_data = lookup_ticker_analytics_from_elastic(timestamp=timestamp)
    analyze_prompt = f"""1. Use Alexander Elder principles to recommend the top {top_n} tickers that are strong entry points based on improving technical indicators and solid fundamental data.
                         2. Create an integer field named 'overall_rank' from 1 to {top_n} based on a detailed review of technical data and an in-depth review of fundamental data.
                         3. Create a field named 'technical_summary' that provides a concise summary (512 tokens or less) of the technical analysis and indicators.
                         4. Create a field named 'fundamental_summary' that provides a concise summary (512 tokens or less) of the fundamental analysis and data.
                         5. Ensure the final output is in JSON format, with the root element named tickers, with the fields 'ticker', 'overall_rank', 'technical_summary', 'fundamental_summary'.
                      """
    top_picks = []
    model = "gpt-4o"
    try:
        response = llm_client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{analyze_prompt}"},
                {"role": "assistant", "content": f"Limit your analysis to the tickers and analytics data provided here: {analytics_data}"},
                {"role": "user", "content": f"tickers"}
            ]
        )
        tickers = json.loads(response.choices[0].message.content)
        logger.info(f"LLM provided top {top_n} tickers by {analyze_prompt} data: {tickers}")
        log_token_count(response, model)
        for ticker in tickers['tickers']:
            ticker_sentiment = generate_sentiment(ticker=ticker["ticker"])
            ticker.update({
                'news_sentiment': ticker_sentiment.get('news_sentiment'),
                'news_summary': ticker_sentiment.get('news_summary')
            })        
            top_picks.append(ticker)
    except Exception as e:
        logger.error(f"Exception: {e}. Failed to provided top tickers by {analyze_prompt} for {top_n} tickers")
        raise e
    return top_picks