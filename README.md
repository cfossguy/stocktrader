## Quickstart

### Step #1 - Install python dependencies
```
pip install poetry
poetry install
poetry shell
```

### Step #2 - Create .env file

POLYGON_API_KEY = ...
ELASTIC_SEARCH_URL = ...
ELASTIC_SEARCH_API_KEY = ...
OPENAI_API_KEY = ...

### Step #3 - Run data pipeline

```
python data_pipeline.py ticker-analytics
python data_pipeline.py ticker-watchlist
```

### Step #4 - Container lifecycle management - data pipeline and s3 listener
```
cd ./containers
manage.py --help
```

### Step #5 - Build ECS image and publish container to ECR

```
docker build --platform linux/amd64 -t jwilliams-stockpicker-datapipeline -f Dockerfile .
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 461485115270.dkr.ecr.us-east-2.amazonaws.com

docker tag jwilliams-stockpicker-datapipeline:latest 461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest
docker push 461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest
```

### Step #6 - Create event bridge to schedule data pipeline in Fargate
```
aws ecs register-task-definition --cli-input-json fileb:///Users/jwilliams/vscode/stockpicker/containers/fargate-task-definition.json

aws ecs run-task \
  --cluster jwilliams-ecs-dev \
  --launch-type FARGATE \
  --task-definition jwilliams-stockpicker-datapipeline-def \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-49862104,subnet-e7f4a58e,subnet-30dc414b],securityGroups=[sg-2a2dc242],assignPublicIp=ENABLED}"
```

### Step #7 - Deploy Eland docker image (for deploying models from huggingface)
```
docker pull docker.elastic.co/eland/eland

docker run -it --rm docker.elastic.co/eland/eland:latest \
    eland_import_hub_model \
      --cloud-id $ELASTIC_CLOUD_ID \
      --es-api-key $ES_API_KEY \
      --hub-model-id intfloat/multilingual-e5-large \
      --task-type text_embedding
```

### Step #8 - Deploy self hosted connector (s3) - JUNK!!!

```
docker pull docker.elastic.co/enterprise-search/elastic-connectors:8.15.0.0

docker run \
  -v "/Users/jwilliams/vscode/stockpicker/connectors/config.yml:/config" \
  --tty \
  --rm \
  docker.elastic.co/enterprise-search/elastic-connectors:8.15.0.0 \
  /app/bin/elastic-ingest \
  -c /config
```

### Step #8 - use logstash to ingest data from s3
```
docker build -t jwilliams-stockpicker-s3-datapipeline -f Dockerfile_S3 .
docker run --hostname stockpicker-s3-container -it jwilliams-stockpicker-s3-datapipeline 
```

### START RAY CLUSTER
```
sudo ray start --head --dashboard-port=8080
```

### CREW AI AGENTS - DeepLearning

data_analyst_agent = Agent(
    role="Data Analyst",
    goal="Monitor and analyze market data in real-time "
         "to identify trends and predict market movements.",
    backstory="Specializing in financial markets, this agent "
              "uses statistical modeling and machine learning "
              "to provide crucial insights. With a knack for data, "
              "the Data Analyst Agent is the cornerstone for "
              "informing trading decisions.",
    verbose=True,
    allow_delegation=True,
    tools = [scrape_tool, search_tool]
)

trading_strategy_agent = Agent(
    role="Trading Strategy Developer",
    goal="Develop and test various trading strategies based "
         "on insights from the Data Analyst Agent.",
    backstory="Equipped with a deep understanding of financial "
              "markets and quantitative analysis, this agent "
              "devises and refines trading strategies. It evaluates "
              "the performance of different approaches to determine "
              "the most profitable and risk-averse options.",
    verbose=True,
    allow_delegation=True,
    tools = [scrape_tool, search_tool]
)

trading_strategy_agent = Agent(
    role="Trading Strategy Developer",
    goal="Develop and test various trading strategies based "
         "on insights from the Data Analyst Agent.",
    backstory="Equipped with a deep understanding of financial "
              "markets and quantitative analysis, this agent "
              "devises and refines trading strategies. It evaluates "
              "the performance of different approaches to determine "
              "the most profitable and risk-averse options.",
    verbose=True,
    allow_delegation=True,
    tools = [scrape_tool, search_tool]
)

### Crew AI TASKS

data_analysis_task = Task(
    description=(
        "Continuously monitor and analyze market data for "
        "the selected stock ({stock_selection}). "
        "Use statistical modeling and machine learning to "
        "identify trends and predict market movements."
    ),
    expected_output=(
        "Insights and alerts about significant market "
        "opportunities or threats for {stock_selection}."
    ),
    agent=data_analyst_agent,
)

strategy_development_task = Task(
    description=(
        "Develop and refine trading strategies based on "
        "the insights from the Data Analyst and "
        "user-defined risk tolerance ({risk_tolerance}). "
        "Consider trading preferences ({trading_strategy_preference})."
    ),
    expected_output=(
        "A set of potential trading strategies for {stock_selection} "
        "that align with the user's risk tolerance."
    ),
    agent=trading_strategy_agent,
)

execution_planning_task = Task(
    description=(
        "Analyze approved trading strategies to determine the "
        "best execution methods for {stock_selection}, "
        "considering current market conditions and optimal pricing."
    ),
    expected_output=(
        "Detailed execution plans suggesting how and when to "
        "execute trades for {stock_selection}."
    ),
    agent=execution_agent,
)

