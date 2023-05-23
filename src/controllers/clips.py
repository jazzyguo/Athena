from s3_client import s3, bucket
from s3_upload import generate_presigned_url
from firestore_client import db
import os

# in firestore, we will have keys of all clips saved/published by the user
# clips.{user_id}: [{
#    key: string
#    url: string
#    saved: boolean // we use a saved flag, to be able to save the video file in case its gone from temp
#    published: {
#       twitter: [{ url, publish_date }]
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

# in s3, we can check the {bucket}/{user_id}/temp_clips folder
# and return signed urls of all the files


def get_temp_clips(user_id):
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


def save_clip(user_id, s3_key):
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
        'saved': True,
        'key': saved_file_path,
        'url': f"https://clips-development.s3.amazonaws.com/{saved_file_path}"
    }

    clips_ref = db.collection('clips').document(user_id)
    clips_doc = clips_ref.get()

    if clips_doc.exists:
        existing_saved_clips = clips_doc.to_dict().get('saved', [])

        for clip in existing_saved_clips:
            if clip['key'] == saved_file_path:
                clip['saved'] = True

        # Update the clips document with the modified array
        clips_ref.update({
            'saved': existing_saved_clips
        })
    else:
        # Create the clips document with the new clip
        clips_ref.set({
            'saved': [new_saved_clip]
        })

    return new_saved_clip


def delete_clip(user_id, s3_key):
    # we get the file from s3 and copy it over to the users {user_id}/temp_clips folder if doesn't exist
    filename = os.path.basename(s3_key)

    temp_file_path = f"{user_id}/temp_clips/{filename}"

    # Check if the file already exists in the temporary clips directory
    response = s3.list_objects_v2(Bucket=bucket, Prefix=temp_file_path)
    file_exists = 'Contents' in response

    # Copy the file to the temporary clips directory if it doesn't exist
    if not file_exists:
        s3.copy_object(Bucket=bucket, Key=temp_file_path, CopySource=s3_key)

    s3.delete_object(Bucket=bucket, Key=s3_key)

    # Update the Firestore document
    clips_ref = db.collection('clips').document(user_id)
    clips_doc = clips_ref.get()

    if clips_doc.exists:
        existing_saved_clips = clips_doc.to_dict().get('saved', [])

        for clip in existing_saved_clips:
            if clip['key'] == s3_key:
                clip['saved'] = False

        clips_ref.update({'saved': existing_saved_clips})

    return 'Success'
