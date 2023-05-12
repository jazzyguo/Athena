from flask import request
from s3_client import s3, bucket
from s3_upload import generate_presigned_url


# in firestore, we will have keys of all clips saved/published by the user


def get_saved_clips():
    user_id = request.args.get('user_id')
    return [user_id]

# in s3, we can check the {bucket}/{user_id}/temp_clips folder
# and return signed urls of all the files


def get_temp_clips():
    user_id = request.args.get('user_id')
    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=f'{user_id}/temp_clips/'
    )
    urls = []
    for obj in response.get('Contents', []):
        url = generate_presigned_url(obj['Key'])
        if url:
            urls.append(url)
    return urls
