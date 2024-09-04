import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import os
import typer
from dotenv import load_dotenv
import time
from setup_environment import logger
import gzip
import shutil

load_dotenv()

app = typer.Typer()
logger = logger("s3_data_pipeline")

bucket_name = 'jwilliams-dev'
local_directory = './s3'

# Specify the source bucket name and prefix
source_bucket_name = 'flatfiles'
prefix = 'us_stocks_sip/minute_aggs_v1/2024/08'

@app.command()
def download_s3_files():
    # Source account credentials
    SOURCE_AWS_ACCESS_KEY_ID = os.getenv('POLYGON_S3_ACCESS_KEY_ID')
    SOURCE_AWS_SECRET_ACCESS_KEY = os.getenv('POLYGON_S3_SECRET_ACCESS_KEY')
    # Initialize a session for the source account
    source_session = boto3.Session(
        aws_access_key_id=SOURCE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=SOURCE_AWS_SECRET_ACCESS_KEY,
    )

    # Create S3 clients for both accounts
    source_s3 = source_session.client(
        's3',
        endpoint_url='https://files.polygon.io',
        config=Config(signature_version='s3v4'),
    )

    # Initialize a paginator for listing objects in the source bucket
    paginator = source_s3.get_paginator('list_objects_v2')
    
    # List and copy objects
    for page in paginator.paginate(Bucket=source_bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            source_object_key = obj['Key']
            file_name = os.path.basename(source_object_key)
            try:
                dest_file_path = f"./s3/{file_name}"
                source_s3.download_file(source_bucket_name, source_object_key, dest_file_path)
                logger.info(f"Downloaded {source_object_key} to {dest_file_path}")
            except ClientError as e:
                logger.error(f"Error copying {source_object_key}: {e}")

def gunzip_file(input_file_path, output_file_path):
    with gzip.open(input_file_path, 'rb') as f_in:
        with open(output_file_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

@app.command()
def upload_s3_files():

    DEST_AWS_ACCESS_KEY_ID = os.getenv('DEST_AWS_ACCESS_KEY_ID')
    DEST_AWS_SECRET_ACCESS_KEY = os.getenv('DEST_AWS_SECRET_ACCESS_KEY')

    # Initialize a session for the destination account
    dest_session = boto3.Session(
        aws_access_key_id=DEST_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=DEST_AWS_SECRET_ACCESS_KEY,
    )

    # Create S3 client for the destination account
    dest_s3 = dest_session.client(
        's3',
        config=Config(signature_version='s3v4'),
    )
    # Assuming local_directory is defined
    files = os.listdir(local_directory)
    cnt = 0
    for file in files:
        local_file_path = os.path.join(local_directory, file)
        if file.endswith('.gz'):
            decompressed_file_path = local_file_path[:-3]  # Remove the .gz extension
            gunzip_file(local_file_path, decompressed_file_path)
            local_file_path = decompressed_file_path  # Update the path to the decompressed file
            s3_key = os.path.relpath(local_file_path, local_directory)
            try:
                logger.info(f"Uploading {local_file_path} to s3://{bucket_name}/{s3_key}")
                dest_s3.upload_file(local_file_path, bucket_name, s3_key)
                os.remove(local_file_path)  # Delete the decompressed file after upload
                cnt += 1
                percentage_complete = (cnt / len(files)) * 100
                logger.info(f"Uploaded {cnt} of {len(files)} files ({percentage_complete:.2f}% complete)")
            except Exception as e:
                logger.error(f"Error uploading {local_file_path}: {e}")

@app.command()
def all():
    start = time.time()
    download_s3_files()
    upload_s3_files()
    end = time.time()
    logger.info(f's3 pipeline duration: {round((end - start) / 60, 2)} minutes')
if __name__ == "__main__":
    app()
    