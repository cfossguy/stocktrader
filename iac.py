from elasticsearch import Elasticsearch
import typer
from dotenv import load_dotenv
import os
import logging
import subprocess
import functools

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
                "_source": ["ticker", "name", "sector", "industry", "beta", "market_cap", "dividend_yield", "rsi_hour", "rsi_day", "rsi_week", "macd_hour", "macd_day", "macd_week", "sma_hour", "pe"],
                "query": {
                    "bool": {
                        "filter": [
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
                "sort": 
                [
                    {
                        "timestamp": {
                            "order": "desc"
                        },
                        "rsi_hour": {
                            "order": "asc"
                        },
                        "rsi_day": {
                            "order": "asc"
                        },
                        "dividend_yield": {
                            "order": "desc"
                        }
                    }      
                ]
            }
        }
    }

    # Index the script template
    response = es_client.put_script(id='ticker_analytics_template', body=script_template)
    print(f"ELASTICSEARCH: Create ticker_analytics search template: {response}")

@catch_exceptions
def create_stockpicker_agent_index():
    es_client = Elasticsearch(hosts=os.getenv('ELASTIC_SEARCH_URL'), api_key=os.getenv('ES_API_KEY'))
    index_name = "stockpicker_agent"
    model_id = ".elser-2-elasticsearch"
    body = {
        "mappings": {
            "properties": {
                "date": { "type": "date", "format": "MM-dd-yyyy"},
                "portfolio_report": { "type": "text", "copy_to": "portfolio_report_semantic" },
                "portfolio_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "technical_report": { "type": "text", "copy_to": "technical_report_semantic" },
                "technical_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "fundamental_report": { "type": "text", "copy_to": "fundamental_report_semantic" },
                "fundamental_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "final_report": { "type": "text", "copy_to": "final_report_semantic" },
                "final_report_semantic": { "type": "semantic_text", "inference_id": model_id },
                "cash_position_usd": { "type": "float" },
                "stock_position_usd": { "type": "float" },
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
                "macd_day": {
                    "type": "long"
                },
                "macd_hour": {
                    "type": "long"
                },
                "macd_week": {
                    "type": "long"
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
def setup_elastic():
    create_ticker_analytics_index()
    create_ticker_analytics_search_template()
    create_ticker_llm_metrics_index()
    create_stockpicker_agent_index()

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
def setup():
    setup_elastic()
    start_ray()

@app.command()
def teardown():
    teardown_elastic()
    stop_ray()

# Example usage:
if __name__ == "__main__":
    app()