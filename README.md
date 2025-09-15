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



