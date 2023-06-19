from api.constants import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_MEDIA_BUCKET, AWS_S3_TEMP_BUCKET
import boto3

temp_bucket = AWS_S3_TEMP_BUCKET or 'famemachine-temp-dev'
media_bucket = AWS_S3_MEDIA_BUCKET or 'famemachine-dev'

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name='us-east-2',
    config=boto3.session.Config(signature_version='s3v4')
)
