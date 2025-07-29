import yfinance_cache as yfc
import time
import random
from datetime import datetime, timedelta, timezone
import traceback
from itertools import islice
from dateutil.parser import parse
import statistics
from statistics import StatisticsError
import logging
from dotenv import load_dotenv
import os
from polygon import RESTClient

load_dotenv()

logger = logging.getLogger("ray")
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

def get_triple_screen_median(ticker: str, timespan='hour', window='10', indicator='rsi'):
    # get week or day or hour rsi for each stock from poloygon.io
    # logger.info(f'Processing {indicator}_{timespan} for {ticker}')
    polygon_client = RESTClient(api_key=POLYGON_API_KEY)
    allowed_timespans = ['hour', 'day', 'week']
    if timespan not in allowed_timespans:
        raise ValueError(f"Invalid timespan '{timespan}'. Allowed values are {allowed_timespans}.")
    allowed_indicators = ['rsi', 'macd', 'sma']
    if indicator not in allowed_indicators:
        raise ValueError(f"Invalid indicator '{indicator}'. Allowed values are {allowed_indicators}.")
    values = []
    try:
        if indicator == 'rsi':
            indicators = polygon_client.get_rsi(ticker=f'{ticker}', timespan=timespan, window=window, adjusted='true', series_type='close', order='desc').values
        elif indicator == 'macd':
            indicators = polygon_client.get_macd(ticker=f'{ticker}', timespan=timespan, short_window='12', long_window='26', signal_window='9', adjusted='true', series_type='close', order='desc').values
        elif indicator == 'sma':
            indicators = polygon_client.get_sma(ticker=f'{ticker}', window=window, timespan=timespan, series_type='close').values
        for r in indicators:
            values.append(r.value)
        median = round(statistics.median(values),2)
        logger.debug(f'{indicator}_{timespan} for {ticker} is: {median}')
        return median
    except IndexError as e:
        logger.debug(f'{indicator}_{timespan} for {ticker} has error - {e}')
        return 0
    except StatisticsError as se:
        logger.debug(f'{indicator}_{timespan} for {ticker} has error - {se}')
        return 0
    
def get_rsi_rank(rsi_hour, rsi_day, rsi_week):
    rsi_rank = 0
    #rank up if rsi is less than 70
    if rsi_hour < 70:
        rsi_rank += 1
    if rsi_day < 70:
        rsi_rank += 1
    if rsi_week < 70:
        rsi_rank += 1
    #rank up if rsi is greater than 30
    if rsi_hour > 30:
        rsi_rank += 1
    if rsi_day > 30:
        rsi_rank += 1
    if rsi_week > 30:
        rsi_rank += 1
    #rank up if short crosses long
    if rsi_hour > rsi_day:
        rsi_rank += 1
    if rsi_day > rsi_week: 
        rsi_rank += 1
    if rsi_day < 50:
        rsi_rank += 1
    if rsi_hour < 50:
        rsi_rank += 1

    return rsi_rank

def get_macd_rank(macd_hour, macd_day, macd_week):
    macd_rank = 0
    #rank up if macd is positive
    if macd_hour > 0:
        macd_rank += 1
    if macd_day > 0:
        macd_rank += 1
    if macd_week > 0:
        macd_rank += 3
    #rank up if macd crosses over
    if macd_hour > macd_day:
        macd_rank += 1
    if macd_day > macd_week:
        macd_rank += 1
    if macd_hour > macd_day and macd_day > 0 and macd_week < 0:
        macd_rank += 3
    
    return macd_rank

def get_pe(ticker):
    polygon_client = RESTClient(api_key=POLYGON_API_KEY)
    pe = 0
    try:
        financials = polygon_client.vx.list_stock_financials(ticker=f'{ticker}')
        eps_list = []

        while len(eps_list) < 4:
            n = next(financials)
            end_date = n.end_date
            basic_earnings_per_share = n.financials.income_statement.basic_earnings_per_share.value
            eps_list.append(basic_earnings_per_share)
            logger.debug(f'basic_earnings={basic_earnings_per_share}, end_date={end_date}')
        previous_close = polygon_client.get_previous_close_agg(ticker=f'{ticker}')[0].close
        yearly_eps = sum(eps_list)
        logger.debug(f'yearly_eps={yearly_eps}, previous_close={previous_close}')
        pe = round(previous_close / yearly_eps,2)
        logger.debug(f'PE for {ticker} is: {pe}')

        return pe

    except IndexError as e:
        logger.debug(f'PE rating for {ticker} has error - {e}. May not have 4 past quarters of financials in polygon.io')
        return pe
    except BaseException as x:
        logger.debug(f'PE rating for {ticker} has error - {x}. May not have 4 past quarters of financials in polygon.io')
        return pe

def get_news(ticker):
    polygon_client = RESTClient(api_key=POLYGON_API_KEY)
    feed_details = str()
    try:
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)

        news = polygon_client.list_ticker_news(ticker=f'{ticker}', limit=100)
        newsfeed = []
        
        for n in islice(news, 100):
            date = parse(n.published_utc)
            if date > three_months_ago:
                description = n.description
                title = n.title
                summary = f"Title: {title}\nDetails: {description}\nDate: {date}\n"
                newsfeed.append(summary)
            
        feed_details = '\n'.join([str(item) for item in newsfeed])
        logger.debug(f'News for {ticker} processed and there are {len(newsfeed)} news items')
        
        return feed_details

    except IndexError as e:
        logger.debug(f'News for {ticker} has error - {e}. May not have data in polygon.io')
        return feed_details
    except BaseException as x:
        logger.debug(f'News for {ticker} has error - {x}. Unknown error polygon.io')
        traceback.print_exc()
        return feed_details
    
def yf_sleep():
    time.sleep(random.uniform(1,3))

def get_market_cap(ticker):
    try:
        ticker = ticker.replace('.', '-')
        ticker_data = yfc.Ticker(ticker)
        market_cap = ticker_data.info['marketCap'] 
        market_cap_in_billion = round(market_cap / 1000000000, 2)
        logger.debug(f'market cap for {ticker} is: {market_cap_in_billion}')
        return market_cap_in_billion
    except (KeyError, TypeError) as e:
        logger.debug(f'market cap {ticker} is: N/A because of {e.__class__.__name__}')
        return None
    except Exception as e:
        logger.debug(f'market cap {ticker} is: N/A because of {e}')
        return None

def get_beta(ticker):
    try:
        time.sleep(random.uniform(1,5))  
        ticker = ticker.replace('.', '-')
        ticker_data = yfc.Ticker(ticker)
        beta = round(ticker_data.info['beta'],2)
        logger.debug(f'beta for {ticker} is: {beta}')
        return beta
    except (KeyError, TypeError) as e:
        logger.debug(f'beta {ticker} is: N/A because of {e.__class__.__name__}')
        return None
    except Exception as e:
        logger.debug(f'market cap {ticker} is: N/A because of {e}')
        return None

def get_dividend_yield(ticker):
    try:
        ticker = ticker.replace('.', '-')
        ticker_data = yfc.Ticker(ticker)
        dividend_yield = round(ticker_data.info['dividendYield'],2)
        logger.debug(f'dividend yield {ticker} is: {dividend_yield}')
        return dividend_yield
    except (KeyError, TypeError) as e:
        logger.debug(f'dividend yield {ticker} is: N/A because of {e.__class__.__name__}')
        return None
    except Exception as e:
        logger.debug(f'dividend yield {ticker} is: N/A because of {e}')
        return None