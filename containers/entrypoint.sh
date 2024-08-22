#!/bin/bash

# Start the Elastic Agent
/app/elastic-agent/elastic-agent run &

# Run the Python application
python /app/data_pipeline.py all
result=$?

# Return the exit code from the Python script
exit $result