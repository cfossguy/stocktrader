from datetime import datetime, timezone
import json
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

def generate_news_summary_and_rank(ticker, news=None):
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
    model = "gpt-4o"

    # Refined prompt for news summary and rank
    combined_prompt = f"""
    You are a financial analysis assistant. Your task is to analyze news articles about {ticker} written in the last 3 months and provide the following:

    1. **Summary**:
       - Extract key financial metrics, trends, and market sentiment from the articles.
       - Summarize the extracted information into a detailed and actionable summary tailored for a financial analyst.
       - Highlight any potential risks, opportunities, or notable events that could impact {ticker}'s performance.

    2. **Sentiment Score**:
       - Parse each statement in the articles.
       - Assign a sentiment score to each statement: +1 for positive, -1 for negative.
       - Aggregate the scores and normalize the final score to a range of 1 to 100.
       - Use this normalized score as the "rank" field in the JSON output.

    Please return the output strictly in the following JSON format, enclosed within <<<JSON>>> and <<<END>>> delimiters:
    <<<JSON>>>
    {{
        "summary": "Your summary here",
        "rank": "Your sentiment score here"
    }}
    <<<END>>>

    The raw news feed data for {ticker} is: {news}
    """

    try:
        # Generate combined response
        combined_response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": combined_prompt}
            ],
            temperature=0,
            top_p=1
        )
        combined_output = combined_response.choices[0].message.content

        # Log the raw response for debugging
        logger.debug(f"Raw combined output: {combined_output}")

        # Extract JSON from delimiters
        try:
            start_idx = combined_output.index("<<<JSON>>>") + len("<<<JSON>>>")
            end_idx = combined_output.index("<<<END>>>")
            json_output = combined_output[start_idx:end_idx].strip()

            # Parse JSON
            combined_data = json.loads(json_output)

            # Ensure required keys exist
            if "summary" not in combined_data or "rank" not in combined_data:
                raise ValueError("Missing required keys in the response JSON")

            summary_text = combined_data.get("summary", "")
            rank = combined_data.get("rank", None)

        except (ValueError, json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse combined output: {combined_output}. Error: {e}")
            summary_text = "Parsing failed for summary."
            rank = None

        # Log token counts for the response
        log_token_count(response=combined_response, model=model)

        return {"summary": summary_text, "rank": rank}

    except Exception as e:
        logger.error(f"Exception: {e}. Failed to generate summary and rank for ticker {ticker}")
        return {"summary": f"News summarization failed for ticker {ticker}.", "rank": None}
    
def generate_fundamentals_summary_and_rank(ticker, financials=None):
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
    model = "gpt-4o"

    prompt = f"""
    You are a financial analysis assistant. Your task is to analyze the fundamentals of {ticker} and provide a ranking based on the following criteria:

    1. **Revenue Growth**:
       - Assess the revenue growth rate over the last 3 years.
       - Provide a percentage growth figure and a brief explanation.

    2. **Profitability**:
       - Evaluate the profit margins (gross, operating, net) for the last fiscal year.
       - Include a comparison to industry averages.

    3. **Debt Levels**:
       - Analyze the debt-to-equity ratio and other relevant metrics.
       - Discuss the implications of the current debt levels on future growth.
    
    4. **Overall Score**:
       - Calculate an overall score from 1-100 based on the above criteria.
       - Use this normalized score as the "rank" field in the JSON output.

    Please return the output strictly in the following JSON format, enclosed within <<<JSON>>> and <<<END>>> delimiters:
    <<<JSON>>>
    {{
        "summary": "Your summary here",
        "rank": "Your overall score here"
    }}
    <<<END>>>

    The raw financial data for {ticker} is: {financials}
    """

    try:
        # Generate response
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt}
            ],
            temperature=0,
            top_p=1
        )
        raw_output = response.choices[0].message.content

        # Log the raw response for debugging
        logger.debug(f"Raw output: {raw_output}")

        # Extract JSON from delimiters
        try:
            start_idx = raw_output.index("<<<JSON>>>") + len("<<<JSON>>>")
            end_idx = raw_output.index("<<<END>>>")
            json_output = raw_output[start_idx:end_idx].strip()

            # Parse JSON
            data = json.loads(json_output)

            # Ensure required keys exist
            if "summary" not in data or "rank" not in data:
                raise ValueError("Missing required keys in the response JSON")

            summary_text = data.get("summary", "")
            rank = data.get("rank", None)

        except (ValueError, json.JSONDecodeError, IndexError) as e:
            logger.debug(f"Failed to parse output: {raw_output}. Error: {e}")
            summary_text = "Parsing failed for summary."
            rank = None

        # Log token counts for the response
        log_token_count(response=response, model=model)

        return {"summary": summary_text, "rank": rank}

    except Exception as e:
        logger.error(f"Exception: {e}. Failed to generate fundamentals summary and rank for ticker {ticker}")
        return {"summary": f"Fundamentals summarization failed for ticker {ticker}.", "rank": None}
