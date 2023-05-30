from flask import abort, jsonify
from athena import process_video
from s3_upload import upload_files_to_s3
import os
import time
import tempfile


def process_file(user_id, uploaded_video):
    filename, file_extension = os.path.splitext(uploaded_video.filename)

    temp_filename = f'{filename}-{int(time.time())}{file_extension}'

    if user_id is None:
        abort(401, 'Access Denied')

    if uploaded_video is None:
        abort(400, 'Required video file is missing')

    clips = []
    uploaded_clips = []

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            temp_filepath = os.path.join(temp_dir, temp_filename)
            uploaded_video.save(temp_filepath)

            clips = process_video(temp_dir, input_file=temp_filepath)
        except ValueError as e:
            abort(400, str(e))

        uploaded_clips = upload_files_to_s3(
            clips, folder_path=f"{user_id}/temp_clips")

    response = jsonify({
        'urls': uploaded_clips
    })

    return response, 200
