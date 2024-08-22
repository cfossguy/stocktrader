#/bin/sh
mkdir -p ./tmp
cp ../*.py ./tmp
cp ../.env ./tmp

poetry export -f requirements.txt --output ./tmp/requirements.txt --without-hashes

# Check if an argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 [data_pipeline|s3_listener]"
  exit 1
fi

# Run the appropriate docker command based on the argument
case "$1" in
  data_pipeline)
    docker build --platform linux/amd64 -t jwilliams-stockpicker-datapipeline -f Dockerfile .
    ;;
  s3_listener)
    docker build --platform linux/amd64 -t jwilliams-stockpicker-s3-listener -f Dockerfile_S3 .
    ;;
  *)
    echo "Invalid option: $1"
    echo "Usage: $0 [option1|option2]"
    exit 1
    ;;
esac
rm -rf ./tmp
