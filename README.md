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

### Step #4 - Build ECS image for the data pipeline
```
poetry export -f requirements.txt --output requirements.txt --without-hashes
docker build --platform linux/amd64 -t jwilliams-stockpicker-datapipeline -f Dockerfile .
```

### Step #5 - Test containerized data pipeline
```
docker run --hostname stockpicker-container -it jwilliams-stockpicker-datapipeline 
```

### Step #6 - Publish container

```
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 461485115270.dkr.ecr.us-east-2.amazonaws.com

docker tag jwilliams-stockpicker-datapipeline:latest 461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest
docker push 461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest

```

#### URI
461485115270.dkr.ecr.us-east-2.amazonaws.com/jwilliams-stockpicker-datapipeline:latest

### Step #7 - Create event bridge to schedule data pipeline
```
aws ecs register-task-definition --cli-input-json fileb:///Users/jwilliams/vscode/stockpicker/task-definition.json

aws ecs run-task \
  --cluster jwilliams-ecs-dev \
  --launch-type FARGATE \
  --task-definition jwilliams-stockpicker-datapipeline-def \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-49862104,subnet-e7f4a58e,subnet-30dc414b],securityGroups=[sg-2a2dc242],assignPublicIp=ENABLED}"
```

```
aws logs tail /ecs/jwilliams-stockpicker-datapipeline --follow
```