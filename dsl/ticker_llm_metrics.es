
DELETE /ticker_llm_metrics

PUT /ticker_llm_metrics
{
  "settings": {
    "index": {
      "sort.field": "timestamp",
      "sort.order": "desc"
    }
  },
  "mappings": {
      "properties": {
        "model_id": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "timestamp": {
          "type": "date"
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
