POST _search/template
{
  "id": "ticker_analytics_template",
  "params": {
            "timestamp": "08-08-2024",
            "rsi_week_gt": 30.00,
            "rsi_week_lt": 70.00,
            "macd_week_gt": 0.00,
            "macd_day_gt": -0.00
        }
}

POST ticker_analytics/_search
{
  "query": {
             "match": {
             "timestamp": "08-07-2024"
             }
         },
         "size": 1000 
}