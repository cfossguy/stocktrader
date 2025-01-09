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