## Quickstart

### Step #1 - Install python dependencies
```
pip install poetry
poetry install
poetry shell
```

### Step #2 - Create .env file

```
POLYGON_API_KEY = ...
ELASTIC_SEARCH_URL = ...
ELASTIC_SEARCH_API_KEY = ...
OPENAI_API_KEY = ...
```
### Step #3 - Provision Elastic Serverless Indexes + Ray
```
python iac.py setup
```

### Step #4 - Run data pipeline
```
python data_pipeline.py run
```

### Step #5 - Teardown Indexes + Ray
```
python iac.py teardown
```

### Serverless Quirks
1. Playground wasn't generating RRF and semantic_text search query blocks right. Made it impossible to test RAG using ELSER or E5 fields. I submitted a feedback form on 1/15 and noticed issue was resolved by 1/30.
2. Somehow, my index got corrupted in a way that blocked document inserts. I could run searches but could not add new documents to the index. Failure was related to one of my semantic fields. Instead of submitting a feedback form, I attempted a re-index. Re-index failed. I also tried to use elasticdump export/import to recover the index. It was able to export my data but not re-import(not sure why but i'm not a typescript fan so I decided to just use python). I ended up creating a manual python script to export the non-semantic fields into JSONL. Then I deleted the index, re-created and used the python script to re-index my data from JSONL backup. This was only acceptable because of the low volume of data. Had my dataset been really large, the python script would have needed tweaks. 

## Most important financial filings

### Bear Market Investing Strategies
1. 10-K SEC Filing - dull language. Key sections: BUSINESS, RISK FACTORS, AUDITORS REPORT - Go back a few years. Pay attention to "notes to statements"(requires company to come clean about everything in 10-K and stock options awards and special item). GAAP and EBITDA. 
2. 10-Q Needs to be taken with grain of salt(not audited)

### TODO

1. Find a way to create a rank feature for earnings. PE ratio isn't a very useful stock screen metric but earnings is. 
2. Create an "earnings" summary text field that is LLM powered. This will pair nicely with the earnings rank_feature.
3. 


