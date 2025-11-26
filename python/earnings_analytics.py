import os
import time
import requests
from typing import List, Dict, Optional

from openai import OpenAI

# =============================
# Config
# =============================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

SEC_HEADERS = {
    # IMPORTANT: per SEC guidelines, use a real, identifying User-Agent
    "User-Agent": "Your Name your_email@example.com",
    "Accept-Encoding": "gzip, deflate",
}

SEC_BASE = "https://data.sec.gov"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

DEFAULT_MODEL = "gpt-4.1-mini"


# =============================
# Helper: Get CIK for ticker
# =============================

def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    Look up the CIK for a given ticker using SEC's ticker metadata.
    Returns zero-padded CIK (10 digits) or None.
    """
    resp = requests.get(TICKERS_URL, headers=SEC_HEADERS)
    resp.raise_for_status()
    data = resp.json()

    ticker_lower = ticker.lower()
    for entry in data.values():
        if entry["ticker"].lower() == ticker_lower:
            cik_int = entry["cik_str"]
            return f"{int(cik_int):010d}"

    return None


# =============================
# Helper: Fetch recent 8-K earnings filings (Item 2.02)
# =============================

def fetch_recent_8k_earnings_filings(cik: str, max_filings: int = 10) -> List[Dict]:
    """
    Fetch the most recent 8-K filings that include Item 2.02 (Results of Operations
    and Financial Condition) for a given CIK.

    max_filings is the maximum number of earnings EVENTS you want (e.g., 8–12).
    """
    url = f"{SEC_BASE}/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=SEC_HEADERS)
    resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    items = recent.get("items", [])  # e.g., "2.02", "2.02,9.01"

    earnings_filings: List[Dict] = []

    for form, acc, date, doc, item_str in zip(
        forms, accession_numbers, filing_dates, primary_docs, items
    ):
        # Filter for 8-Ks that include Item 2.02
        if form == "8-K" and item_str and "2.02" in item_str:
            earnings_filings.append(
                {
                    "form": form,
                    "accession_number": acc,
                    "filing_date": date,
                    "primary_doc": doc,
                    "items": item_str,
                }
            )
        if len(earnings_filings) >= max_filings:
            break

    return earnings_filings


# =============================
# Helper: Download the filing text
# =============================

def download_filing_text(cik: str, accession_number: str, primary_doc: str) -> str:
    """
    Download the primary document (HTML or text) for a filing.
    """
    acc_no_nodash = accession_number.replace("-", "")
    # CIK in path is *not* zero-padded
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_nodash}/{primary_doc}"

    resp = requests.get(url, headers=SEC_HEADERS)
    resp.raise_for_status()
    return resp.text


# =============================
# LLM client
# =============================

def get_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=OPENAI_API_KEY)


# =============================
# Stage 1: Per-filing mini-summary
# =============================

def summarize_single_earnings_8k(
    ticker: str,
    filing_meta: Dict,
    filing_text: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Use the LLM to produce a compact, per-filing summary of a single
    8-K (Item 2.02) earnings release.

    Output: short markdown-style text with:
      - Period / filing date (from meta)
      - 2–4 bullets on rev/EPS vs prior period, key drivers, guidance
    """
    client = get_openai_client()

    # Trim filing text to control token usage (adjust as needed)
    trimmed = filing_text[:8000]

    filing_label = (
        f"{filing_meta['form']} | Filed: {filing_meta['filing_date']} | "
        f"Accession: {filing_meta['accession_number']} | Items: {filing_meta.get('items', '')}"
    )

    system_msg = (
        "You are a financial analysis assistant. "
        "You read a single Form 8-K earnings release (Item 2.02) and write a "
        "very compact summary focusing on earnings performance. "
        "Be concise and use only information in the text."
    )

    user_msg = f"""
Ticker: {ticker}
Filing: {filing_label}

Task:
- Read the following 8-K (Item 2.02) earnings release excerpt.
- Produce a short markdown summary with:
  - A one-line heading like: "Qx YYYY Earnings Snapshot"
  - 2–4 bullet points covering:
    - Revenue direction vs prior-year or prior-period (if mentioned)
    - EPS direction vs prior-year or prior-period (if mentioned)
    - Major drivers (e.g., segments, margin changes, costs, FX, one-offs)
    - Any explicit guidance or outlook commentary
- If a metric is not clearly stated, say that it is not specified rather than guessing.

Earnings 8-K excerpt:
\"\"\"
{trimmed}
\"\"\"
    """.strip()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.25,
    )

    return response.choices[0].message.content


# =============================
# Stage 2: Trend synthesis over all mini-summaries
# =============================

def summarize_earnings_trend_over_time(
    ticker: str,
    per_filing_summaries: List[str],
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Take the compact summaries for the last N earnings events and
    synthesize short- and medium-term earnings trends.
    """
    client = get_openai_client()

    # Build combined text of mini-summaries
    combined = []
    for i, s in enumerate(per_filing_summaries, start=1):
        combined.append(f"\n\n=== Earnings Event #{i} (older events appear later or earlier depending on input order) ===\n{s}")

    content = "".join(combined)

    system_msg = (
        "You are a financial analysis assistant specializing in earnings trends. "
        "You are given compact summaries of several consecutive earnings events for one company. "
        "You must analyze both short-term (most recent few quarters) and medium-term trends."
    )

    user_msg = f"""
You are analyzing the earnings history for ticker {ticker}.
You are given summarized earnings snapshots for recent Form 8-K earnings releases
(Item 2.02). Use ONLY the information in these summaries.

Please do the following:

1. **Chronology**
   - Assume the summaries are ordered from most recent to oldest *if the caller provides them that way*.
   - If the chronology is unclear, infer it from dates or period labels in the summaries and explain any assumptions.

2. **Short-Term Trend (Last 4 Earnings Events)**
   - State clearly whether revenue and EPS appear to be trending UP, DOWN, MIXED, or FLAT over roughly the last 4 earnings events.
   - Comment on consistency versus volatility.
   - Reference specific quarters or periods (e.g., "Q1 2025", "Q3 FY24") when possible.

3. **Medium-Term Trend (Last 8–12 Earnings Events if available)**
   - Describe the broader direction of earnings across the full history:
     - Improving, deteriorating, stable, or mixed?
   - Highlight any patterns:
     - Sustained acceleration/slowdown in revenue
     - Margin expansion/compression
     - Repeated beats/misses if implied
     - Repeated upgrades/downgrades to guidance

4. **Key Drivers & Themes**
   - Summarize recurring drivers (e.g., particular segments, cost discipline, FX headwinds).
   - Note any clear structural or strategic shifts that show up over multiple events.

5. **Limitations**
   - Briefly call out any important missing information (e.g., no explicit EPS trends given, limited guidance).

Keep the final answer structured and concise, with clear section headings:
- "Short-Term Earnings Trend"
- "Medium-Term Earnings Direction"
- "Key Drivers and Themes"
- "Limitations"
    
Here are the per-filing summaries:

{content}
    """.strip()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.25,
    )

    return response.choices[0].message.content


# =============================
# Main function: end-to-end analysis from 8-Ks
# =============================

def analyze_ticker_earnings_trend_from_8k(
    ticker: str,
    max_events: int = 10,
    per_filing_model: str = DEFAULT_MODEL,
    trend_model: str = DEFAULT_MODEL,
) -> str:
    """
    End-to-end pipeline:

    1. Takes a ticker symbol.
    2. Looks up the most recent `max_events` Form 8-K filings with Item 2.02 from sec.gov.
    3. For each 8-K:
       - Downloads the primary document.
       - Uses an LLM to create a compact per-filing earnings summary.
    4. Uses a second LLM call to analyze:
       - Short-term trend (roughly last 4 earnings events)
       - Medium-term direction (up to last 8–12 events)

    Returns the final LLM trend summary as a string.
    """
    cik = get_cik_for_ticker(ticker)
    if not cik:
        raise ValueError(f"Could not find CIK for ticker {ticker}")

    # Fetch recent earnings 8-Ks
    filings = fetch_recent_8k_earnings_filings(cik, max_filings=max_events)
    if not filings:
        raise ValueError(
            f"No recent 8-K Item 2.02 earnings filings found for {ticker} (CIK {cik})"
        )

    per_filing_summaries: List[str] = []

    for idx, f in enumerate(filings, start=1):
        print(
            f"[{idx}/{len(filings)}] Downloading {f['form']} (Items {f.get('items')}) "
            f"filed {f['filing_date']}..."
        )
        txt = download_filing_text(cik, f["accession_number"], f["primary_doc"])

        # Stage 1: mini-summary for this filing
        print(f"Summarizing earnings event {idx}...")
        mini_summary = summarize_single_earnings_8k(
            ticker=ticker,
            filing_meta=f,
            filing_text=txt,
            model=per_filing_model,
        )
        per_filing_summaries.append(mini_summary)

        # Be polite to SEC and your LLM provider
        time.sleep(0.25)

    # Stage 2: trend synthesis across all mini-summaries
    print("Analyzing earnings trend across events...")
    final_summary = summarize_earnings_trend_over_time(
        ticker=ticker,
        per_filing_summaries=per_filing_summaries,
        model=trend_model,
    )

    return final_summary


# =============================
# Example usage
# =============================

if __name__ == "__main__":
    # Example: analyze last 10 earnings events for AAPL
    ticker = "AAPL"
    summary = analyze_ticker_earnings_trend_from_8k(ticker, max_events=10)
    print(summary)