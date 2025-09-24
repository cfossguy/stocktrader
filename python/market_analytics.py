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
import math
import requests
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

def get_rsi_rank(
    rsi_hour: float,
    rsi_day: float,
    rsi_week: float,
    prev_rsi_hour: float | None = None,
    prev_rsi_day: float | None = None,
    prev_rsi_week: float | None = None,
    weights: dict | None = None,
) -> dict:
    """
    Triple-screen RSI rank for initiating/adding long positions.
    Returns a 0–100 score plus reasons.
    """

    # ---- weights (sum ~1.0) ----
    w = {
        "weekly_regime": 0.40,
        "daily_pullback": 0.35,
        "hourly_trigger": 0.20,
        "risk_penalties": 0.05,
    }
    if weights:
        w.update(weights)

    reasons = []

    # ---- helpers ----
    def clamp01(x): 
        return max(0.0, min(1.0, x))

    def triangular_score(x, lo, hi, ideal):
        """1.0 at 'ideal', linearly down to 0.0 at lo/hi, 0 outside."""
        if x <= lo or x >= hi:
            return 0.0
        if x == ideal:
            return 1.0
        if x < ideal:
            return (x - lo) / (ideal - lo)
        else:
            return (hi - x) / (hi - ideal)

    def band_penalty(x, overbought=70, oversold=30):
        """Small penalties for extremes; returns value in [-1, 0]."""
        if x >= overbought:
            # scale penalty up to -1 as x approaches 100
            return -min(1.0, (x - overbought) / (100 - overbought))
        if x <= oversold:
            # scale penalty up to -1 as x approaches 0
            return -min(1.0, (oversold - x) / oversold)
        return 0.0

    def crossed_up(curr, prev, level):
        return prev is not None and prev < level <= curr

    # ---- 1) Weekly regime (trend filter) ----
    # Prefer weekly between ~55–65 (healthy bull). Still decent above 50.
    weekly_core = triangular_score(rsi_week, lo=50, hi=75, ideal=60)  # 50..75 peak at 60
    weekly_score = weekly_core

    # Rising weekly gets a small boost
    if prev_rsi_week is not None and rsi_week >= 50 and rsi_week > prev_rsi_week:
        weekly_score = clamp01(weekly_score + 0.15)
        reasons.append("Weekly RSI rising above 50 (trend supportive).")
    else:
        if rsi_week >= 50:
            reasons.append("Weekly RSI ≥ 50 (bullish regime).")
        else:
            reasons.append("Weekly RSI < 50 (trend not supportive).")

    # ---- 2) Daily pullback (buy-the-dip zone) ----
    # Best zone for entries during bull regime: ~40–50, ideal ~45
    daily_core = triangular_score(rsi_day, lo=35, hi=55, ideal=45)
    daily_score = daily_core

    # Deep buyable dip bonus if weekly regime is bullish and daily is 30–40
    if rsi_week >= 50 and 30 <= rsi_day < 40:
        daily_score = clamp01(daily_score + 0.15)
        reasons.append("Daily RSI in attractive dip zone with bullish weekly regime.")

    # ---- 3) Hourly trigger (timing) ----
    hourly_score = triangular_score(rsi_hour, lo=45, hi=60, ideal=52)  # prefer early turn-up
    trigger_notes = []

    if crossed_up(rsi_hour, prev_rsi_hour, 50):
        hourly_score = clamp01(hourly_score + 0.25)
        trigger_notes.append("Hourly crossed up through 50.")
    if prev_rsi_hour is not None and prev_rsi_day is not None:
        if prev_rsi_hour < prev_rsi_day <= rsi_hour:
            hourly_score = clamp01(hourly_score + 0.20)
            trigger_notes.append("Hourly crossed up through Daily.")

    if trigger_notes:
        reasons.extend(trigger_notes)
    else:
        reasons.append("Hourly near 50 (timing okay).")

    # ---- 4) Risk penalties for extremes ----
    # Mild global penalties for any timeframe at extremes.
    penalties = [
        band_penalty(rsi_week),
        band_penalty(rsi_day),
        band_penalty(rsi_hour),
    ]
    # If weekly < 50, apply an extra regime penalty (we’re fighting trend)
    if rsi_week < 50:
        penalties.append(-0.25)
        reasons.append("Penalty: Weekly < 50 (fighting trend).")

    penalty_score = clamp01(1.0 + sum(penalties))  # maps into [0,1]; lower if more penalties

    # ---- Weighted blend -> 0..100 ----
    blended = (
        w["weekly_regime"] * weekly_score
        + w["daily_pullback"] * daily_score
        + w["hourly_trigger"] * hourly_score
        + w["risk_penalties"] * penalty_score
    )
    final_score = round(100 * clamp01(blended), 1)

    # ---- Label for quick interpretation ----
    if final_score >= 80:
        label = "A+ setup"
    elif final_score >= 65:
        label = "Attractive"
    elif final_score >= 50:
        label = "Neutral/Watch"
    else:
        label = "Avoid/Wait"

    reasons.append(
        f"Weekly={rsi_week:.1f}, Daily={rsi_day:.1f}, Hourly={rsi_hour:.1f} → {label}"
    )
    logger.info({"score": final_score, "label": label, "reasons": reasons})
    # Ensure final_score is at least 0.000001
    return max(final_score, 0.000001)

def _pos_strength(x: float, scale: float = 1.0) -> float:
    """
    Map MACD value to [0, 1] with diminishing returns.
    scale ~ 'how big is a meaningful MACD' for your symbols/timeframe.
    """
    return 0.5 * (math.tanh(x / scale) + 1.0)

def get_macd_rank(macd_hour: float, macd_day: float, macd_week: float, scale: float = 1.0) -> int:
    """
    Triple-screen MACD attractiveness score in [0, 100].
    Inputs are current MACD values (not histograms) for hour/day/week.
    """
    # 1) Base trend strength (weekly > daily > hourly)
    base = (
        50 * _pos_strength(macd_week, scale) +   # anchor trend
        30 * _pos_strength(macd_day, scale)  +   # tactical trend
        20 * _pos_strength(macd_hour, scale)     # timing
    )

    # 2) Alignment / acceleration bonuses
    bonus = 0

    # All positive = strong alignment
    if macd_week > 0 and macd_day > 0 and macd_hour > 0:
        bonus += 12

    # Monotonic acceleration H ≥ D ≥ W (momentum building across TFs)
    if macd_hour >= macd_day >= macd_week:
        bonus += 10

    # Early reversal: higher TF still negative but lower TFs flipped positive
    if macd_week < 0 and macd_day > 0 and macd_hour > 0:
        bonus += 8

    # Hour leading day (short-term crossover tendency)
    if macd_hour > macd_day:
        bonus += 4

    # 3) Conflict penalties (reduce whipsaw / mixed signals)
    penalty = 0
    negatives = sum(v <= 0 for v in (macd_hour, macd_day, macd_week))
    if negatives >= 2:
        penalty += 12  # broadly bearish across TFs
    elif macd_week <= 0 and macd_day <= 0 and macd_hour > 0:
        penalty += 6   # only intraday positive against higher-TF downtrend

    # 4) Clamp to [0, 100]
    score = max(0.000001, min(100, round(base + bonus - penalty)))
    return score

def get_news(ticker):
    polygon_client = RESTClient(api_key=POLYGON_API_KEY)
    news_items = []
    try:
        now = datetime.now(timezone.utc)
        duration = now - timedelta(days=90)

        news = polygon_client.list_ticker_news(ticker=f'{ticker}', limit=100)

        for n in islice(news, 100):
            date = parse(n.published_utc)
            if date > duration:
                item = {
                    "title": n.title if hasattr(n, 'title') else "",
                    "details": n.description if hasattr(n, 'description') else "",
                    "date": str(date)
                }
                news_items.append(item)
        print(f'Found {len(news_items)} news items for {ticker} in the last 90 days.')
        print(news_items)
        logger.debug(f'News for {ticker} processed and there are {len(news_items)} news items')
        return news_items

    except IndexError as e:
        logger.debug(f'News for {ticker} has error - {e}. May not have data in polygon.io')
        return news_items
    except BaseException as x:
        logger.debug(f'News for {ticker} has error - {x}. Unknown error polygon.io')
        traceback.print_exc()
        return news_items

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
    
def get_balance_sheets(ticker):
    """
    Fetches balance sheet data for a ticker using Polygon REST API.
    Returns a list of balance sheets or None if not found/error.
    """
    url = f"https://api.polygon.io/stocks/financials/v1/balance-sheets?tickers={ticker}&timeframe=quarterly&limit=12&sort=period_end.desc&apiKey={POLYGON_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "OK" and data.get("results"):
            return data["results"]
        else:
            logger.debug(f"No balance sheets found for {ticker}: {data}")
            return None
    except Exception as e:
        logger.debug(f"Error fetching balance sheets for {ticker}: {e}")
        return None
        
def get_ratios(ticker):
    """
    Fetches financial ratios for a ticker using Polygon REST API.
    Returns a dict of ratios or None if not found/error.
    """
    url = f"https://api.polygon.io/stocks/financials/v1/ratios?ticker={ticker}&limit=1&sort=ticker.asc&apiKey={POLYGON_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            # Drop 'cik' and 'date' keys if present
            result.pop('cik', None)
            result.pop('date', None)
            return result
        else:
            logger.debug(f"No ratios found for {ticker}: {data}")
            return None
    except Exception as e:
        logger.debug(f"Error fetching ratios for {ticker}: {e}")
        return None

