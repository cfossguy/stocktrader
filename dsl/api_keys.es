DELETE /_security/api_key
{
  "name": "stocktrader"
}

POST /_security/api_key
{
  "name": "stocktrader",
  "expiration": "60d",   
  "role_descriptors": { 
        "role-application": {
        "cluster": ["all"],
        "indices": [
            {
            "names": ["ticker*"],
            "privileges": ["read", "write", "create_index", "view_index_metadata"]
            }
        ]
        }
    },
    "metadata": {
        "application": "stocktrader",
        "environment": {
        "level": 1,
        "trusted": true,
        "tags": ["dev", "staging"]
        }
    }
}


POST /_security/api_key
{
  "name": "elastic-agent",
  "expiration": "60d",   
  "role_descriptors": { 
        "role-agent": {
        "cluster": ["monitor", "manage_index_templates", "manage_ilm", "manage_ingest_pipeline", "create_doc", "create_index"],
        "indices": [
            {
            "names": ["logs-*", "metrics-*"],
            "privileges": ["create_index", "create", "delete", "write", "auto_configure", "manage", "read"]
            }
        ]
        }
    },
    "metadata": {
        "application": "stocktrader",
        "environment": {
        "level": 1,
        "trusted": true,
        "tags": ["dev", "staging"]
        }
    }
}

POST /_security/api_key
{
  "name": "filebeat",
  "expiration": "60d",   
  "role_descriptors": { 
        "role-application": {
        "cluster": ["all"],
        "indices": [
            {
            "names": ["filebeat*"],
            "privileges": ["read", "write", "create_index", "view_index_metadata"]
            }
        ]
        }
    },
    "metadata": {
        "application": "stocktrader",
        "environment": {
        "level": 1,
        "trusted": true,
        "tags": ["dev", "staging"]
        }
    }
}
