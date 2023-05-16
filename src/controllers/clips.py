from flask import request, abort
from s3_client import s3, bucket
from s3_upload import generate_presigned_url
from firestore_client import db
import os
from google.cloud import firestore

# in firestore, we will have keys of all clips saved/published by the user
# clips.{user_id}: [{
#    key: string
#    url: string
#
#    published: {
#       twitter: [{ url, publish_date }]
#    }
# }]


def get_saved_clips():
    user_id = request.args.get('user_id')

    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=f'{user_id}/saved_clips/'
    )

    s3_objects = []

    for obj in response.get('Contents', []):
        key = obj['Key']
        created_at = obj['LastModified']
        url = obj['Url']

        if url:
            s3_objects.append({
                "url": url,
                "key": key,
                "created_at": created_at
            })

    sorted_objects = sorted(
        s3_objects, key=lambda x: x['created_at'], reverse=True)

    return sorted_objects

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

    sorted_objects = sorted(
        s3_objects, key=lambda x: x['created_at'], reverse=True)

    return sorted_objects


def save_clip():
    json_data = request.get_json()

    if json_data:
        user_id = json_data.get('user_id')
        s3_key = json_data.get('s3_key')

        # we get the file from s3 and copy it over to the users {user_id}/saved_clips folder
        temp_file_path = s3_key
        filename = os.path.basename(s3_key)

        saved_file_path = f"{user_id}/saved_clips/{filename}"

        s3.copy_object(
            Bucket=bucket,
            Key=saved_file_path,
            CopySource={
                'Bucket': bucket, 'Key':
                temp_file_path
            }
        )

        # we also add to the users.clips within firestore
        new_saved_clip = {
            'key': saved_file_path,
            'url': f"https://clips-development.s3.amazonaws.com/{saved_file_path}"
        }

        clips_ref = db.collection('clips').document(user_id)

        if clips_ref.get().exists:
            existing_saved_clips = clips_ref.get().to_dict().get('saved', [])
            existing_keys = {clip['key'] for clip in existing_saved_clips}

            if saved_file_path not in existing_keys:
                # Update the clips document with the new clip
                clips_ref.update({
                    'saved': firestore.ArrayUnion([new_saved_clip])
                })
        else:
            # Create the clips document with the new clip
            clips_ref.set({
                'saved': [new_saved_clip]
            })

        # Return the updated document from Firestore
        document = clips_ref.get().to_dict()

        return document

    else:
        abort(400, 'Params missing')
