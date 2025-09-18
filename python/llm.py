from datetime import datetime, timezone
import json
import logging
import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from openai import OpenAI
import pytz
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from statistics import mean

load_dotenv()

ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
ES_API_KEY = os.getenv('ES_API_KEY')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
LLM_DEBUG_RESP = os.getenv("LLM_DEBUG_RESP", "0") in ("1", "true", "True")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID")

logger = logging.getLogger("ray")

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
    
# --- Helpers -----------------------------------------------------------------

def _try_parse_date(s: str) -> Optional[datetime]:
    """Best-effort ISO/near-ISO parser without external deps."""
    if not s:
        return None
    s = s.strip()
    # Normalize trailing Z
    s = s.replace("Z", "+00:00")
    # Common fast paths
    fmts = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    # Last resort: extract YYYY-MM-DD
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        except Exception:
            return None
    return None

def _dedup_by_title_date(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Collapse near-duplicates by normalized title (lower/trim) + same-day date.
    Keep the most recent per (title_key, yyyy-mm-dd).
    """
    best = {}
    for it in items:
        t = (it.get("title") or "").strip().lower()
        d = it.get("date_dt")
        day = d.date().isoformat() if d else "nodate"
        key = (t, day)
        if key not in best:
            best[key] = it
        else:
            # keep the one with a later timestamp if available
            if (it.get("date_dt") or datetime.min.replace(tzinfo=timezone.utc)) > (
                best[key].get("date_dt") or datetime.min.replace(tzinfo=timezone.utc)
            ):
                best[key] = it
    return list(best.values())


def preprocess_news(
    raw_news: List[Dict[str, Any]],
    ticker: str,
    aliases: Optional[List[str]] = None,
    now: Optional[datetime] = None,
    max_items: int = 15,
    detail_chars: int = 360,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    - Parse dates
    - Filter to last 90 days
    - Relevance by ticker/aliases (title/details)
    - De-duplicate
    - Truncate details
    - Keep most recent N
    Returns compact items: [{title, date, details}]
    """
    if not raw_news:
        return []

    aliases = aliases or []
    now = now or datetime.now(timezone.utc)
    min_date = now - timedelta(days=90)

    prepped = []
    for n in raw_news:
        title = (n.get("title") or "").strip()
        details = (n.get("details") or "").strip()
        date_str = (n.get("date") or "").strip()

        # Parse & window filter
        dt = _try_parse_date(date_str)
        if not dt or dt < min_date or dt > now:
            continue

        # Truncate details (strip boilerplate-ish tails)
        clean_details = re.sub(r"\s+", " ", details)[:detail_chars]

        prepped.append(
            {
                "title": title,
                "date": dt.isoformat(),
                "details": clean_details,
                "date_dt": dt,  # for sorting/dedup
            }
        )

    if not prepped:
        return []

    # De-duplicate and sort desc
    prepped = _dedup_by_title_date(prepped)
    prepped.sort(key=lambda x: x["date_dt"], reverse=True)

    # Trim to max_items and drop helper field
    compact = []
    for it in prepped[:max_items]:
        compact.append(
            {
                "title": it["title"],
                "date": it["date"],
                "details": it["details"],
            }
        )
    return compact


# --- Main --------------------------------------------------------------------

def generate_news_summary_and_rank(
    ticker: str,
    news: Optional[List[Dict[str, Any]]] = None,
    aliases: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Faster path: A + C + D
    - A: preprocess on client (filter/trim/dedup/cap)
    - C: concise prompt
    - D: force JSON output with small max_tokens
    """
    llm_client = OpenAI(api_key=OPENAI_API_KEY)

    compact_items = preprocess_news(
        raw_news=news or [],
        ticker=ticker,
        aliases=aliases or [],
        max_items=15,
        detail_chars=360,
        keywords=keywords,
    )

    # If empty after preprocessing, short-circuit with a deterministic default
    if not compact_items:
        return {
            "summary": "No eligible news in the last 90 days. Treat older items as qualitative context only.",
            "rank": 50,
        }

    system_msg = (
        "You are a financial analysis assistant. "
        "Using only the provided items (title, date, details<=360 chars), return a concise JSON with "
        'keys {"summary": string, "rank": integer 1..100}. '
        "Prioritize 0–30 day catalysts/risks; use 31–90 day items as context. "
        "Do not invent facts or entities. If items appear repetitive, consolidate the event in the summary."
    )

    user_payload = {
        "ticker": ticker,
        # Keep payload small—already filtered/capped
        "items": compact_items,
        # A tiny nudge without long guardrails:
        "scoring_hint": "Rank reflects net business impact from the items; 50 = neutral/mixed."
    }

    try:
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL_ID,
            response_format={"type": "json_object"},
            temperature=0.1, max_tokens=1024, top_p=0.9, frequency_penalty=0.1, presence_penalty=0.1,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
        content = resp.choices[0].message.content
        data = json.loads(content)

        # Defensive checks
        summary = data.get("summary", "").strip()
        rank = data.get("rank", 50)
        if not isinstance(rank, int):
            # Try coercion; fallback to neutral
            try:
                rank = int(round(float(rank)))
            except Exception:
                rank = 50
        # Clip to [1, 100]
        rank = max(1, min(100, rank))

        return {"summary": summary, "rank": rank}

    except Exception as e:
        # Keep failures fast and deterministic
        return {
            "summary": f"LLM summarization failed for {ticker}: {e}",
            "rank": 50,
        }
    
def _safe_div(n, d):
    try:
        return n / d if d not in (0, None) and n is not None else None
    except Exception:
        return None

def compute_scores(financials: list[dict]) -> Dict[str, Any]:
    """
    Compute TTM revenue, growth, margins, D/E, subscores, and overall rank locally.
    Expects minimal fields present in your payload.
    """
    # ---- Extract last 4 periods for TTM (newest first or last agnostic) ----
    periods = sorted(financials, key=lambda p: p.get("end_date", ""))[-4:]  # last 4 by end_date
    revs = []
    op = []
    net = []
    for p in periods:
        fs = p.get("financials", {})
        inc = fs.get("income_statement", {}) or {}
        revs.append(inc.get("revenues"))
        op.append(inc.get("operating_income_loss"))
        net.append(inc.get("net_income_loss"))

    def _sum_or_none(xs):
        xs2 = [x for x in xs if isinstance(x, (int, float))]
        return sum(xs2) if xs2 else None

    ttm_rev = _sum_or_none(revs)
    ttm_op = _sum_or_none(op)
    ttm_net = _sum_or_none(net)

    # Build base (previous 4 periods) for TTM growth if available
    base_periods = sorted(financials, key=lambda p: p.get("end_date", ""))[-8:-4]
    base_ttm_rev = None
    if len(base_periods) == 4:
        base_revs = []
        for p in base_periods:
            inc = (p.get("financials", {}) or {}).get("income_statement", {}) or {}
            base_revs.append(inc.get("revenues"))
        base_ttm_rev = _sum_or_none(base_revs)

    # Margins
    op_margin = _safe_div(ttm_op, ttm_rev)
    net_margin = _safe_div(ttm_net, ttm_rev)

    # D/E proxy from most recent period with data
    de_proxy = None
    for p in sorted(financials, key=lambda p: p.get("end_date", ""), reverse=True):
        bs = (p.get("financials", {}) or {}).get("balance_sheet", {}) or {}
        equity = bs.get("equity")
        long_term_debt = bs.get("long_term_debt")
        liabilities = bs.get("liabilities")
        if equity is None or (isinstance(equity, (int, float)) and equity <= 0):
            continue
        if isinstance(long_term_debt, (int, float)):
            de_proxy = long_term_debt / equity
            break
        if isinstance(liabilities, (int, float)):
            de_proxy = liabilities / equity
            break

    # ---- Scoring (integers) ----
    # Revenue growth score
    growth_pct = None
    if ttm_rev is not None and base_ttm_rev not in (None, 0):
        growth_pct = ((ttm_rev / base_ttm_rev) - 1.0) * 100.0

    def growth_to_score(g):
        if g is None: return 50
        if g <= -20: return 20
        if g <= 0:   return 40
        if g <= 5:   return 55
        if g <= 10:  return 70
        if g <= 20:  return 80
        if g <= 40:  return 90
        return 95

    revenue_growth_score = int(growth_to_score(growth_pct))

    # Profitability score
    def op_score(m):
        if m is None: return None
        m *= 100
        if m <= 0:  return 35
        if m <= 5:  return 55
        if m <= 10: return 70
        if m <= 20: return 80
        return 90

    def net_score(m):
        if m is None: return None
        m *= 100
        if m <= 0:  return 30
        if m <= 5:  return 55
        if m <= 10: return 70
        if m <= 20: return 80
        return 90

    subs = [s for s in (op_score(op_margin), net_score(net_margin)) if s is not None]
    profitability_score = int(round(mean(subs))) if subs else 50

    # Debt score
    if de_proxy is None:
        debt_score = 50
    else:
        d = de_proxy
        if d <= 0.5: debt_score = 90
        elif d <= 1.0: debt_score = 80
        elif d <= 2.0: debt_score = 65
        elif d <= 3.0: debt_score = 50
        elif d <= 5.0: debt_score = 35
        else: debt_score = 20

    overall = int(round(revenue_growth_score*0.30 + profitability_score*0.40 + debt_score*0.30))

    return {
        "metrics": {
            "ttm_revenue": ttm_rev,
            "base_ttm_revenue": base_ttm_rev,
            "growth_percent": None if growth_pct is None else int(round(growth_pct)),
            "operating_margin_percent": None if op_margin is None else int(round(op_margin*100)),
            "net_margin_percent": None if net_margin is None else int(round(net_margin*100)),
            "de_proxy": None if de_proxy is None else float(de_proxy),
        },
        "scores": {
            "revenue_growth_score": revenue_growth_score,
            "profitability_score": profitability_score,
            "debt_score": debt_score,
            "rank": overall
        }
    }

def summarize_fundamentals(ticker: str, computed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Small LLM: produce concise summary only, with JSON response_format.
    """
    m = computed["metrics"]
    s = computed["scores"]

    # tiny payload (few tokens)
    compact_context = {
        "ticker": ticker,
        "metrics": m,
        "scores": {
            "revenue_growth": s["revenue_growth_score"],
            "profitability": s["profitability_score"],
            "debt": s["debt_score"]
        },
        "rank": s["rank"]
    }

    system = (
        "You are a financial analysis assistant. Using ONLY the provided metrics and scores, "
        "write a concise, neutral, analyst-ready fundamentals summary (≤200 words). "
        "Do not add numbers that are not present. Mention any missing metrics neutrally. "
        "Return a JSON object with keys: summary and rank."
    )

    user = {
        "instruction": "Summarize and return JSON.",
        "context": compact_context
    }

    llm_client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        # Send the user payload as a compact JSON string to avoid Python's repr()
        resp = llm_client.chat.completions.create(
            model=LLM_MODEL_ID,
            temperature=0.1, max_tokens=1024, top_p=0.9, frequency_penalty=0.1, presence_penalty=0.1,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            # Force strict JSON & short output
            response_format={"type": "json_object"}
        )

        # Inspect choices safely
        out = None
        try:
            choices = getattr(resp, "choices", None) or resp.get("choices") if isinstance(resp, dict) else getattr(resp, "choices", None)
            logger.debug(f"LLM choices: {choices}")
            if choices and len(choices) > 0:
                # Try attribute access first, then dict-style
                first = choices[0]
                msg = getattr(first, "message", None) or first.get("message") if isinstance(first, dict) else getattr(first, "message", None)
                out = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
        except Exception as _:
            out = None

        # Fallback to older access pattern if above didn't yield content
        if out is None:
            try:
                out = resp.choices[0].message.content
            except Exception:
                try:
                    out = resp["choices"][0]["message"]["content"]
                except Exception:
                    out = None

        # Log token usage if available
        try:
            usage = getattr(resp, "usage", None) or (resp.get("usage") if isinstance(resp, dict) else None)
            if usage:
                pt = getattr(usage, "prompt_tokens", None) or usage.get("prompt_tokens") if isinstance(usage, dict) else None
                ct = getattr(usage, "completion_tokens", None) or usage.get("completion_tokens") if isinstance(usage, dict) else None
                logger.debug(f"LLM usage - prompt_tokens: {pt}, completion_tokens: {ct}")
        except Exception:
            pass
        # response_format=json_object should make content a JSON string; ensure we return it
        if isinstance(out, (dict, list)):
            # Already parsed
            return {"raw": json.dumps(out, ensure_ascii=False)}
        if isinstance(out, str):
            # Handle empty string case explicitly
            if not out.strip():
                logger.error(f"Empty response content for {ticker}")
                fallback = {
                    "summary": "LLM returned empty content",
                    "rank": computed.get("scores", {}).get("rank", 50),
                    "reasoning_trace": {"metrics": computed.get("metrics"), "scores": computed.get("scores")}
                }
                return {"raw": json.dumps(fallback, ensure_ascii=False)}
            
            # Try to ensure it's valid JSON by parsing then re-serializing
            try:
                parsed = json.loads(out)
                return {"raw": json.dumps(parsed, ensure_ascii=False)}
            except Exception:
                # Not JSON parseable; still return raw string for debugging
                return {"raw": out}

    except Exception as e:
        logger.error(f"summarize_fundamentals LLM error for {ticker}: {e}")
        # Deterministic fallback: include computed metrics so caller can still use result
        fallback = {
            "summary": f"LLM call failed: {str(e)}",
            "rank": computed.get("scores", {}).get("rank", 50),
            "reasoning_trace": {"metrics": computed.get("metrics"), "scores": computed.get("scores")}
        }
        return {"raw": json.dumps(fallback, ensure_ascii=False)}

def generate_fundamentals_summary_and_rank(ticker: str, financials: Optional[list]=None):
    computed = compute_scores(financials or [])
    llm_json = summarize_fundamentals(ticker, computed)
    # Parse llm_json["raw"] and return only summary and rank
    try:
        parsed = json.loads(llm_json["raw"])
        summary = parsed.get("summary", "")
        rank = parsed.get("rank", 50)
        logger.info(f"Fundamentals summary for {ticker}: {{'summary': {summary}, 'rank': {rank}}}")
        return {"summary": summary, "rank": rank}
    except Exception:
        # Fallback: return empty summary and neutral rank
        logger.info(f"Fundamentals summary for {ticker}: {{'summary': '', 'rank': 50}} (fallback)")
        return {"summary": "", "rank": 50}
