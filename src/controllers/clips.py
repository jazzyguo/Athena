from flask import request
from s3_client import s3, bucket
from s3_upload import generate_presigned_url
from datetime import datetime


# in firestore, we will have keys of all clips saved/published by the user


def get_saved_clips():
    user_id = request.args.get('user_id')
    return []

# in s3, we can check the {bucket}/{user_id}/temp_clips folder
# and return signed urls of all the files


def get_temp_clips():
    user_id = request.args.get('user_id')
    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=f'{user_id}/temp_clips/'
    )

    s3_objects = []

    for obj in response.get('Contents', []):
        key = obj['Key']
        created_at = obj['LastModified']

        url = generate_presigned_url(obj['Key'])

        if url:
            s3_objects.append({
                "url": url,
                "key": key,
                "created_at": created_at
            })

    sorted_objects = sorted(s3_objects, key=lambda x: x['created_at'])

    return sorted_objects
