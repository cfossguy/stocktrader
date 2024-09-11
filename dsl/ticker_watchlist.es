DELETE /ticker_watchlist
DELETE _ingest/pipeline/ticker_watchlist_pipeline
DELETE /_enrich/policy/ticker_watchlist_enrich_policy

PUT /_enrich/policy/ticker_watchlist_enrich_policy
{
  "match": {
    "indices": "ticker_analytics",
    "match_field": "ticker",
    "enrich_fields": ["name", "sector", "industry",
                      "rsi_hour", "rsi_day", "rsi_week", "macd_hour", "macd_day",
                      "macd_week", "sma_hour", "sma_day", "sma_week", "beta",
                      "market_cap", "dividend_yield", "pe"]
  }
}

POST /_enrich/policy/ticker_watchlist_enrich_policy/_execute

PUT _ingest/pipeline/ticker_watchlist_pipeline
{
  "description": "A pipeline to add a sparse vector field using ELSER",
  "processors": [
    {
      "inference": {
        "model_id": ".elser_model_2_linux-x86_64",
        "input_output": [
          {
            "input_field": "news_summary",
            "output_field": "news_summary_embedding"
          }
        ]
      }
    },
    {
      "inference": {
        "model_id": ".elser_model_2_linux-x86_64",
        "input_output": [
          {
            "input_field": "technical_summary",
            "output_field": "technical_summary_embedding"
          }
        ]
      }
    },
    {
      "inference": {
        "model_id": ".elser_model_2_linux-x86_64",
        "input_output": [
          {
            "input_field": "fundamental_summary",
            "output_field": "fundamental_summary_embedding"
          }
        ]
      }
    },
    {
      "enrich": {
        "policy_name": "ticker_watchlist_enrich_policy",
        "field": "ticker",
        "target_field": "enriched_data"
      }
    },
    {
      "script": {
        "source": """
          // Flatten the enriched data then remove
          if (ctx.enriched_data != null) {
            ctx.name = ctx.enriched_data.name;
            ctx.sector = ctx.enriched_data.sector;
            ctx.industry = ctx.enriched_data.industry;
            ctx.rsi_hour = ctx.enriched_data.rsi_hour;
            ctx.rsi_day = ctx.enriched_data.rsi_day;
            ctx.rsi_week = ctx.enriched_data.rsi_week;
            ctx.macd_hour = ctx.enriched_data.macd_hour;
            ctx.macd_day = ctx.enriched_data.macd_day;
            ctx.macd_week = ctx.enriched_data.macd_week;
            ctx.sma_hour = ctx.enriched_data.sma_hour;
            ctx.sma_day = ctx.enriched_data.sma_day;
            ctx.sma_week = ctx.enriched_data.sma_week;
            ctx.beta = ctx.enriched_data.beta;
            ctx.market_cap = ctx.enriched_data.market_cap;
            ctx.dividend_yield = ctx.enriched_data.dividend_yield;
            ctx.pe = ctx.enriched_data.pe;
            ctx.date = ctx.timestamp;
            ctx.remove('enriched_data');
          }

          // Flatten the context so it can be used for RAG queries
          def result = new ArrayList();
          result.add('date' + ': ' + ctx.timestamp);
          result.add('name' + ': ' + ctx.name);
          result.add('sector' + ': ' + ctx.sector);
          result.add('industry' + ': ' + ctx.industry);
          result.add('rsi_hour' + ': ' + ctx.rsi_hour);
          result.add('rsi_day' + ': ' + ctx.rsi_day);
          result.add('rsi_week' + ': ' + ctx.rsi_week);
          result.add('macd_hour' + ': ' + ctx.macd_hour);
          result.add('macd_day' + ': ' + ctx.macd_day);
          result.add('macd_week' + ': ' + ctx.macd_week);
          result.add('sma_hour' + ': ' + ctx.sma_hour);
          result.add('sma_day' + ': ' + ctx.sma_day);
          result.add('sma_week' + ': ' + ctx.sma_week);
          result.add('beta' + ': ' + ctx.beta);
          result.add('market_cap' + ': ' + ctx.market_cap);
          result.add('dividend_yield' + ': ' + ctx.dividend_yield);
          result.add('pe' + ': ' + ctx.pe);
          result.add('ticker' + ': ' + ctx.ticker);
          result.add('overall_rank' + ': ' + ctx.overall_rank);
          result.add('technical_summary' + ': ' + ctx.technical_summary);
          result.add('fundamental_summary' + ': ' + ctx.fundamental_summary);
          result.add('news_sentiment' + ': ' + ctx.news_sentiment);
          result.add('news_summary' + ': ' + ctx.news_summary);
          ctx.context_flattened = String.join(" | ", result);
        """
      }
    }
  ]
}

PUT /_index_template/ticker_watchlist_template
{
  "index_patterns": ["ticker_watchlist*"],
  "template": {
    "settings": {
      "default_pipeline": "ticker_watchlist_pipeline"
    }
  }
}

PUT /ticker_watchlist
{
    "mappings": {
        "dynamic": "true",
        "properties": {
            "timestamp": {
                "type": "date",
                "format": "MM-dd-yyyy"
            },
            "date": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "ticker": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "overall_rank": {"type": "integer" },
            "news_summary": { "type": "text"},
            "news_sentiment": {"type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "technical_summary": { "type": "text"},
            "fundamental_summary": { "type": "text" },
            "news_summary_embedding": { "type": "sparse_vector" },
            "technical_summary_embedding": { "type": "sparse_vector" },
            "fundamental_summary_embedding": { "type": "sparse_vector" },
            "name": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "sector": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "industry": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "rsi_day": { "type": "long" },
            "rsi_hour": { "type": "long" },
            "rsi_week": { "type": "long" },
            "macd_day": { "type": "float" },
            "macd_hour": { "type": "float" },
            "macd_week": { "type": "float" },
            "sma_day": { "type": "long" },
            "sma_hour": { "type": "long" },
            "sma_week": { "type": "long" },
            "beta": { "type": "float" },
            "market_cap": { "type": "float" },
            "dividend_yield": { "type": "float" },
            "pe": { "type": "float" },
            "enriched_data": { 
              "type": "nested"
              }
            }
        }
}

GET /ticker_watchlist/_search