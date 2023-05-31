from botocore.exceptions import ClientError
import os
from typing import List
from s3_client import s3, bucket
from datetime import datetime
import pytz

expiration = 86400


def generate_timestamp():
    # Get the current timestamp in GMT format like s3 does
    gmt = pytz.timezone('GMT')
    current_time = datetime.now(gmt)
    timestamp = current_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
    return timestamp 


def generate_presigned_url(file_name, expiration=86400):
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


def upload_file_to_s3(folder_path: str, file_path: str, file_prefix: str):
    file_name = f"{folder_path}/{file_prefix}{os.path.basename(file_path)}"
    s3.upload_file(file_path, bucket, file_name)
    url = generate_presigned_url(file_name)

    timestamp = generate_timestamp()

    uploaded_file = {
        "url": url,
        "key": file_name,
        "created_at": timestamp
    }

    return uploaded_file


def upload_files_to_s3(file_paths: List[str], **kwargs):
    folder_path: str = kwargs.get(
        'folder_path', ''
    )
    file_prefix: str = kwargs.get(
        'file_prefix', ''
    )

    uploaded_files = []

    for file_path in file_paths:
        try:
            s3_url = upload_file_to_s3(folder_path, file_path, file_prefix)
            uploaded_files.append(s3_url)
        except Exception as e:
            print(f'Error uploading {file_path}: {str(e)}')

    return uploaded_files
