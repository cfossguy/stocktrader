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