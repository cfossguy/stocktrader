from elasticsearch import Elasticsearch, helpers
import typer
from dotenv import load_dotenv
import os
import logging
import subprocess
import functools
import json

app = typer.Typer()

load_dotenv()

ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
ES_API_KEY = os.getenv('ES_API_KEY')

def catch_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{func.__name__}: {e}")
    return wrapper

@catch_exceptions
def create_ticker_analytics_search_template():
    es_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    script_template = {
        "script": {
            "lang": "mustache",
            "source": {
                "size": 100,
                "retriever": {
                    "linear": {
                        "rank_window_size": 1000,
                        "filter": {
                            "bool": {
                                "must": [
                                    {
                                        "range": {
                                            "rsi_day": {
                                                "gt": "{{rsi_day_gt}}",
                                                "lt": "{{rsi_day_lt}}"
                                            }
                                        }
                                    },
                                    {
                                        "range": {
                                            "macd_week": {
                                                "gt": "{{macd_week_gt}}",
                                                "lt": "{{macd_week_lt}}"
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        "retrievers": [
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "rank_feature": {
                                                "field": "rsi_rank"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.3
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "rank_feature": {
                                                "field": "macd_rank"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.3
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "rank_feature": {
                                                "field": "news_rank"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.1
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "rank_feature": {
                                                "field": "fundamentals_rank"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.3
                            }
                        ]
                    }
                }
            }
        }
    }

@catch_exceptions
def create_ticker_analytics_search_by_ticker_template():
    es_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    script_template = {
        "script": {
            "lang": "mustache",
            "source": """
            { 
                "size": {{size}},
                "query": {
                    "match": {
                        "ticker": "{{ticker}}"
                    }
                },
                "sort": [
                    {
                        "timestamp": {
                            "order": "desc"
                        }
                    }
                ]
            }
            """
        }
    }
    # Index the script template
    response = es_client.put_script(id='ticker_analytics_lookup_template', body=script_template)
    print(f"ELASTICSEARCH: Create ticker_analytics_lookup_template: {response}")

@catch_exceptions
def create_stockpicker_search_template():
    es_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY)
    script_template = {
        "script": {
            "lang": "mustache",
            "source": """
            {
                {{#semantic}}
                "size": {{size}},
                "_source": { "includes": ["date"] },
                "retriever": {
                    "linear": {
                        "rank_window_size": 100,
                        "retrievers": [
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "semantic": {
                                                "field": "final_report_semantic",
                                                "query": "{{query}}"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.6
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "semantic": {
                                                "field": "fundamental_report_semantic",
                                                "query": "{{query}}"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.1
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "semantic": {
                                                "field": "portfolio_report_semantic",
                                                "query": "{{query}}"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.1
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "semantic": {
                                                "field": "screen_report_semantic",
                                                "query": "{{query}}"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.1
                            },
                            {
                                "retriever": {
                                    "standard": {
                                        "query": {
                                            "semantic": {
                                                "field": "technical_report_semantic",
                                                "query": "{{query}}"
                                            }
                                        }
                                    }
                                },
                                "weight": 0.1
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "final_report_semantic": {
                            "type": "semantic",
                            "number_of_fragments": 2,
                            "order": "score"
                        },
                        "fundamental_report_semantic": {
                            "type": "semantic",
                            "number_of_fragments": 2,
                            "order": "score"
                        },
                        "portfolio_report_semantic": {
                            "type": "semantic",
                            "number_of_fragments": 2,
                            "order": "score"
                        },
                        "screen_report_semantic": {
                            "type": "semantic",
                            "number_of_fragments": 2,
                            "order": "score"
                        },
                        "technical_report_semantic": {
                            "type": "semantic",
                            "number_of_fragments": 2,
                            "order": "score"
                        }
                    }
                }
                {{/semantic}}
                {{^semantic}}
                "size": {{size}},
                "query": {
                        "match_all": {}
                    },
                "sort": [
                    {
                        "date": {
                            "order": "desc"
                        }
                    }
                ]
                {{/semantic}}
            }
            """
        }
    }

    # Index the script template
    response = es_client.put_script(id='stockpicker_agent_template', body=script_template)
    print(f"ELASTICSEARCH: Create stockpicker_agent search template: {response}")

@catch_exceptions
def create_stockpicker_agent_index():
    es_client = Elasticsearch(hosts=os.getenv('ELASTIC_SEARCH_URL'), api_key=os.getenv('ES_API_KEY'))
    index_name = "stockpicker_agent"
    model_id = ".elser-2-elasticsearch"
    body = {
        "mappings": {
            "properties": {
                "date": { "type": "date", "format": "MM-dd-yyyy"},
                "screen_report": { "type": "text", "copy_to": "screen_report_semantic" },
                "screen_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "portfolio_report": { "type": "text", "copy_to": "portfolio_report_semantic" },
                "portfolio_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "technical_report": { "type": "text", "copy_to": "technical_report_semantic" },
                "technical_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "fundamental_report": { "type": "text", "copy_to": "fundamental_report_semantic" },
                "fundamental_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "etf_report": { "type": "text", "copy_to": "etf_report_semantic" },
                "etf_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "final_report": { "type": "text", "copy_to": "final_report_semantic" },
                "final_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "cash_position_usd": { "type": "float" },
                "stock_position_usd": { "type": "float" },
                "account_balance": { "type": "float" },
                "stocks_owned": {
                    "type": "nested",
                    "properties": {
                        "ticker": { "type": "keyword" },
                        "total_usd": { "type": "float"}
                    }
                }
            }
        }
    }

    response = es_client.indices.create(index=index_name, body=body)
    print(f"ELASTICSEARCH: create {index_name} index: {response}")

@catch_exceptions
def create_ticker_analytics_index():
    es_client = Elasticsearch(hosts=os.getenv('ELASTIC_SEARCH_URL'), api_key=os.getenv('ES_API_KEY'))
    index_name = "ticker_analytics"
    body = {
        "settings": {
            "index": {
                "sort.field": "timestamp",
                "sort.order": "desc"
            }
        },
        "mappings": {
            "dynamic": "false",
            "properties": {
                "Date added": {
                    "type": "text"
                },
                "beta": {
                    "type": "float"
                },
                "dividend_yield": {
                    "type": "float"
                },
                "industry": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "news_summary": { "type": "text"},
                "news_rank": {
                    "type": "rank_feature"
                },
                "fundamentals_summary": { "type": "text"},
                "fundamentals_rank": {
                    "type": "rank_feature"
                },
                "macd_day": {
                    "type": "long"
                },
                "macd_hour": {
                    "type": "long"
                },
                "macd_week": {
                    "type": "long"
                },
                "macd_rank": {
                    "type": "rank_feature"
                },
                "market_cap": {
                    "type": "float"
                },
                "name": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "pe": {
                    "type": "float"
                },
                "rsi_day": {
                    "type": "long"
                },
                "rsi_hour": {
                    "type": "long"
                },
                "rsi_week": {
                    "type": "long"
                },
                "rsi_rank": {
                    "type": "rank_feature"
                },
                "sector": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "sma_day": {
                    "type": "long"
                },
                "sma_hour": {
                    "type": "long"
                },
                "sma_week": {
                    "type": "long"
                },
                "ticker": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "timestamp": {
                    "type": "date",
                    "format": "MM-dd-yyyy"
                }
            }
        }
    }

    response = es_client.indices.create(index=index_name, body=body)
    print(f"ELASTICSEARCH: create {index_name} index: {response}")

@catch_exceptions
def update_ticker_analytics_index():
    es_client = Elasticsearch(hosts=os.getenv('ELASTIC_SEARCH_URL'), api_key=os.getenv('ES_API_KEY'))
    index_name = "ticker_analytics"
    body = {
        "properties": {
            "macd_rank": {
                "type": "rank_feature"
            },
            "rsi_rank": {
                "type": "rank_feature"
            },
            "news_rank": {
                "type": "rank_feature"
            },
            "fundamentals_rank": {
                "type": "rank_feature"
            },
            "fundamentals_summary": { "type": "text"}
        }
    }

    response = es_client.indices.put_mapping(index=index_name, body=body)
    print(f"ELASTICSEARCH: update {index_name} index: {response}")

@catch_exceptions
def create_ticker_llm_metrics_index():
    es_client = Elasticsearch(hosts=os.getenv('ELASTIC_SEARCH_URL'), api_key=os.getenv('ES_API_KEY'))
    index_name = "ticker_llm_metrics"
    body = {
        "settings": {
            "index": {
                "sort.field": "timestamp",
                "sort.order": "desc"
            }
        },
        "mappings": {
            "dynamic": "false",
            "properties": {
                "timestamp": {
                    "type": "date"
                },
                "model_id": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "input_token_count": {
                    "type": "long"
                },
                "output_token_count": {
                    "type": "long"
                }
            }
        }
    }

    response = es_client.indices.create(index=index_name, body=body)
    print(f"ELASTICSEARCH: create ticker_llm_metrics index: {response}")

@app.command()
def update_settings():
    update_ticker_analytics_index()
    create_ticker_analytics_search_template()
    create_stockpicker_search_template()
    create_ticker_analytics_search_by_ticker_template()

@app.command()
def setup_elastic():
    create_ticker_analytics_index()
    create_ticker_analytics_search_template()
    create_stockpicker_search_template()
    create_ticker_llm_metrics_index()
    create_stockpicker_agent_index()

@app.command()
def backup_data(index_name: str):

    # Initialize the Elasticsearch client
    es_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY, request_timeout=600)
    
    # Define the backup file name
    backup_file = f'{index_name}_backup.jsonl'

    # Open the backup file for writing
    with open(backup_file, 'w') as f:
        # Use the helpers.scan function to retrieve all documents from the index
        for doc in helpers.scan(es_client, index=index_name):
            # Filter out fields that end with "semantic"
            filtered_doc = {k: v for k, v in doc['_source'].items() if not (k.endswith('semantic') or k.endswith('_e5'))}
            # Write the filtered document to the backup file in JSONL format
            f.write(json.dumps(filtered_doc) + '\n')

    print(f'Backup of index "{index_name}" completed successfully and saved to "{backup_file}".')

@app.command()
def restore_data(index_name: str):

    # Initialize the Elasticsearch client
    es_client = Elasticsearch(hosts=ELASTIC_SEARCH_URL, api_key=ES_API_KEY, request_timeout=600)

    # Define the backup file name
    backup_file = f'{index_name}_backup.jsonl'

    # Open the backup file for reading
    with open(backup_file, 'r') as f:
        # Read each line in the backup file
        actions = [
            {
                "_index": index_name,
                "_source": json.loads(line),
                "_id": json.loads(line).get('date')
            }
            for line in f
        ]

    # Use the helpers.bulk function to insert all documents into the index
    helpers.bulk(es_client, actions)

    print(f'Restore of index "{index_name}" completed successfully from "{backup_file}".')

@app.command()
def teardown_elastic():
    es_client = Elasticsearch(hosts=os.getenv('ELASTIC_SEARCH_URL'), api_key=os.getenv('ES_API_KEY'))
    response = es_client.indices.delete(index='ticker_analytics')
    print(f"ELASTICSEARCH: delete ticker_analytics index: {response}")
    response = es_client.delete_script(id='ticker_analytics_template')
    print(f"ELASTICSEARCH: delete ticker_analytics query template: {response}")
    response = es_client.indices.delete(index='ticker_llm_metrics')
    print(f"ELASTICSEARCH: delete ticker_llm_metrics index: {response}")
    response = es_client.indices.delete(index='stockpicker_agent')
    print(f"ELASTICSEARCH: delete stockpicker_agent index: {response}")

@app.command()
@catch_exceptions
def start_ray():
    command = ["ray", "start", "--head", "--dashboard-port=8080"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print("RAY: started successfully")
    else:
        print("RAY: failed to start. It's probably already running or a permissions issue.")

@app.command()
@catch_exceptions
def stop_ray():
    command = ["ray", "stop"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print("RAY: stopped successfully")
        print(result.stdout)
    else:
        print("RAY: failed to stop")
        print(result.stderr)

@app.command()
def teardown():
    teardown_elastic()

# Example usage:
if __name__ == "__main__":
    app()