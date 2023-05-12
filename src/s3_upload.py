from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
import boto3
from botocore.exceptions import ClientError
import os
from typing import List

bucket = 'clips-development'
expiration = 3600

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name='us-east-2',
    config=boto3.session.Config(signature_version='s3v4')
)


def generate_presigned_url(file_name, expiration=3600):
    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': file_name
            },
            ExpiresIn=expiration
        )

    except ClientError as e:
        print(f'Error generating presigned URL: {e}')
        return None

    return response


def upload_file_to_s3(user_id: str, file_path: str) -> str:
    file_name = f"{user_id}/{os.path.basename(file_path)}"
    s3.upload_file(file_path, bucket, file_name)
    url = generate_presigned_url(file_name)
    return url


def upload_files_to_s3(file_paths: List[str], **kwargs) -> List[str]:
    user_id: str = kwargs.get(
        'user_id', ''
    )

    uploaded_files = []

    for file_path in file_paths:
        try:
            s3_url = upload_file_to_s3(user_id, file_path)
            uploaded_files.append(s3_url)
        except Exception as e:
            print(f'Error uploading {file_path}: {str(e)}')

    return uploaded_files
