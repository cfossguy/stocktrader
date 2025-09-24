## Quickstart

### Step #1 - Install python dependencies
```
pip install poetry
poetry install
poetry shell
```

### Step #2 - Create .env file

*_PATH and *_DIR entries must be absolute paths. 

```
OPENAI_API_KEY=...
# Elasticsearch configuration
ELASTIC_SEARCH_URL=...
ES_API_KEY=...

POLYGON_API_KEY=...

PY_PIPELINE_PATH=[YOUR_PROJECT_ABSOLUTE_PATH]/data_pipeline.py
PY_CREW_AI_PATH=[YOUR_PROJECT_ABSOLUTE_PATH]/crew_ai.py
LOCAL_DATA_DIR=[YOUR_PROJECT_ABSOLUTE_PATH]/data

# hack for clearing py-yfinance-cache daily. cache is needed to keep from getting rate limited
YAHOO_FINANCE_CACHE_DIR=[YOUR_USER_HOME_ABSOLUTE_PATH]/Library/Caches/py-yfinance-cache

# used to set the model id in mastra, crewai and llm.py (FYI - gpt5 kind of works but is slower and doesn't produce better results yet)
LLM_MODEL_ID=gpt-4o-mini
```
### Step #3 - Provision Elastic Serverless Indexes + Ray
```
python iac.py setup
```

### Step #4 - Start Mastra
Open: http://localhost:4111/agents then click "Commander"

- run data pipeline with a prompt like: "run stockpicker workflow"
- get buy/sell recommendations with a prompt like: "what stocks should i buy/sell today?"
- find out if any stocks show up as a sell in last 10 reports: "do any buy candidates show up as "sell" in last 10 reports?"
- run a semantic search: "Can you run a semantic search for "industrial stocks with good dividend yield?"

### Step #5 - Open Mastra
```
./start.sh
```

## run stockpicker workflow
## what stocks should i buy/sell today?
## do any buy candidates show up as sell in last 10 reports?
## can you run a semantic search for telco stocks with a good dividend yield?

## Interesting experimental prompts

### Discrepencies and Conflicts
TICKER=WMT
run a semantic search on last 10 crewai reports and highlight conflicting buy/sell recommendations for {TICKER}?

### Entry / Exit - Tickers
TICKER=WMT
run analytics lookup on {TICKER} with size=10 and provide thoughts on a good limit buy price range? 

TICKER=WMT,PURCHASE_PRICE=??.??,CURRENT_PRICE=??.??
can you run analytics lookup on {TICKER} with size=10 and provide thoughts on good stop limit range? i bought it at {PURCHASE_PRICE} and it is currently trading at {CURRENT_PRICE}.

### Inverse ETFS
ETF=QQQ,CURRENT_PRICE=598
can you run analytics lookup and crewai report semantic search on {ETF} with size=10 and provide thoughts on a good short entry point? i want to set a conditional order that triggers once the ETF falls off it's high and is about to breach a key short term support level. it is currently trading at {CURRENT_PRICE}.




