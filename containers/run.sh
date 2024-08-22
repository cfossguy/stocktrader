#!/bin/bash

# Check if an argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 [data_pipeline|s3_listener]"
  exit 1
fi

# Run the appropriate docker command based on the argument
case "$1" in
  data_pipeline)
    docker run --hostname jwilliams-stockpicker-datapipeline -it jwilliams-stockpicker-datapipeline
    ;;
  s3_listener)
    docker run --hostname jwilliams-stockpicker-s3-listener -it jwilliams-stockpicker-s3-listener
    ;;
  *)
    echo "Invalid option: $1"
    echo "Usage: $0 [option1|option2]"
    exit 1
    ;;
esac