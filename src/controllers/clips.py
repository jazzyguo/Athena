from flask import jsonify
from config.s3_client import s3, media_bucket, temp_bucket
from utils.s3_upload import generate_presigned_url, generate_timestamp
from config.firestore_client import db

# in firestore, we will have keys of all clips saved/published by the user
# clips.{user_id}.saved: [{
#    key: string
#    url: string
#    saved: boolean // we use a saved flag, to be able to save the video file in case its gone from temp
#    published: {
#       twitter: [{ url, published_at }]
#    }
# }]
# When we save a clip, we store it in firestore and move in s3 {user_id}/temp_clips/file_name to {user_id}/saved_clips/file_name
#
# When we delete a clip, we change the saved boolean on the collection to false, delete the saved s3 file,
# and move it back into the temp dir. This is because we don't want to lose published information,
# and we are then able to let the user resee the clip in their temp dir which would normally expire after 24hr


def get_saved_clips(user_id):
    clips_ref = db.collection('clips').document(user_id)

    results = []

    if clips_ref.get().exists:
        saved_clips = clips_ref.get().to_dict().get('saved', [])
        results = [clip for clip in saved_clips if clip.get('saved', False)]

    return results

# in s3, we can check the temp bucket folder
# and return signed urls of all the files


def get_temp_clips(user_id):
    response = s3.list_objects_v2(
        Bucket=temp_bucket,
        Prefix=f'{user_id}/'
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


def save_clip(user_id, s3_key):
    exists = False # we append to firestore

    clips_ref = db.collection('clips').document(user_id)
    clips_doc = clips_ref.get()

    new_saved_clip = {
        'saved': True,
        'key': s3_key,
        'url': f"https://{media_bucket}.s3.amazonaws.com/{s3_key}"
    }

    if clips_doc.exists:
        existing_saved_clips = clips_doc.to_dict().get('saved', [])

        for clip in existing_saved_clips:
            if clip['key'] == s3_key:
                exists = True
                clip['saved'] = True

        if exists == False:
            existing_saved_clips.append(new_saved_clip)

        # Update the clips document with the modified array
        clips_ref.update({
            'saved': existing_saved_clips
        })
    else:
        # Create the clips document with the new clip
        clips_ref.set({
            'saved': [new_saved_clip]
        })

    # we get the file from s3 and copy it over to the media folder
    s3.copy_object(
        Bucket=media_bucket,
        Key=s3_key,
        CopySource={
            'Bucket': temp_bucket, 
            'Key': s3_key
        }
    )

    return new_saved_clip


def delete_clip(user_id, s3_key):
    # we get the file from s3 and copy it over to the users temp bucket if doesn't exist

    # Check if the file already exists in the temp bucket
    response = s3.list_objects_v2(Bucket=temp_bucket, Prefix=s3_key)
    file_exists = 'Contents' in response

    # Copy the file to the temporary clips directory if it doesn't exist
    if not file_exists:
        s3.copy_object(
            Bucket=temp_bucket, 
            Key=s3_key, 
            CopySource={
                'Bucket': media_bucket, 
                'Key': s3_key,
            }
        )

    s3.delete_object(Bucket=media_bucket, Key=s3_key)

    # Update the Firestore document
    clips_ref = db.collection('clips').document(user_id)
    clips_doc = clips_ref.get()

    if clips_doc.exists:
        existing_saved_clips = clips_doc.to_dict().get('saved', [])

        for clip in existing_saved_clips:
            if clip['key'] == s3_key:
                clip['saved'] = False

        clips_ref.update({'saved': existing_saved_clips})

    # return the new temp signed url
    temp_url = generate_presigned_url(s3_key)

    timestamp = generate_timestamp()

    return jsonify({
        'url': temp_url, 
        'key': s3_key, 
        'created_at': timestamp
    }), 200
