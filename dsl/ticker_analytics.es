
DELETE /ticker_analytics

PUT /ticker_analytics
{
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

POST _scripts/ticker_analytics_template
{
  "script": {
    "lang": "mustache",
    "source": {
      "size": 1000,
      "query": {
        "bool": {
          "must": [
            {
              "match": {
                "timestamp": "{{timestamp}}"
              }
            }
          ],
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
      }
    }
  }
}