import logging
from dotenv import load_dotenv
from polygon import RESTClient
from openai import OpenAI
import os
from elasticsearch import Elasticsearch
from ecs_logging import StdlibFormatter
import logging.handlers 

load_dotenv()

def logger(program_name: str) -> logging.Logger:
    logger = logging.getLogger(program_name)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(StdlibFormatter())
        logger.addHandler(handler)
        try:
            file_handler = logging.FileHandler('/var/log/python_app.out.log')
            file_handler.setFormatter(StdlibFormatter())
            logger.addHandler(file_handler)
        except:
            print("app logger permission issue. continuing without it")
    
    return logger
    
def polygon_client() -> RESTClient:
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
    polygon_client = RESTClient(api_key=POLYGON_API_KEY)
    return polygon_client

def llm_client() -> OpenAI:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
    return llm_client

def elastic_client() -> Elasticsearch:
    ELASTIC_SEARCH_URL = os.getenv('ELASTIC_SEARCH_URL')
    ELASTIC_SEARCH_API_KEY = os.getenv('ELASTIC_SEARCH_API_KEY')
    
    elastic_client = Elasticsearch(ELASTIC_SEARCH_URL,
                                   api_key=ELASTIC_SEARCH_API_KEY)

    return elastic_client