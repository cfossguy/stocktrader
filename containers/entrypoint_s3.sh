#!/bin/bash

# Start the Elastic Agent
#/usr/share/logstash/elastic-agent/elastic-agent run &

# Start logstash s3 listener
/usr/share/logstash/bin/logstash

# Return the exit code from the Python script
exit $result