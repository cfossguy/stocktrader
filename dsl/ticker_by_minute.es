DELETE /ticker_by_minute

PUT /ticker_by_minute
{
  "mappings": {
    "dynamic": "false", 
    "properties": {
      "ticker": {
        "type": "keyword"
      },
      "volume": {
        "type": "integer"
      },
      "open": {
        "type": "float"
      },
      "close": {
        "type": "float"
      },
      "high": {
        "type": "float"
      },
      "low": {
        "type": "float"
      },
      "window_start_ms": {
         "type": "date"
      },
      "transactions": {
        "type": "integer"
      }
    }
  }
}
GET /ticker_by_minute/_search

GET /ticker_by_minute/_count