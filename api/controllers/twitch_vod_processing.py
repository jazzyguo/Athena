from flask import abort, jsonify
from api.utils import process_video
from api.s3 import upload_files_to_s3
import os
import time
import tempfile
import subprocess
import datetime
from api.firestore import db
from api.constants import MODE


def format_duration(duration_seconds):
    duration = datetime.timedelta(seconds=int(duration_seconds))
    return str(duration)

# vid files are saved in s3 in {user_id}/temp_clips/twitch-{vod_id}-{timestamp now}_frames-{start}to{end}.mp4


def twitch_vod_processing(vod_id, start_time, end_time, user_id):
    clips = []
    uploaded_clips = []

    # fetch twitch access token using user_id
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if user_doc.exists:
        access_token = user_doc.get('connections').get(
            'twitch').get('access_token')

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                temp_filename = f'{vod_id}-{int(time.time())}.mp4'

                temp_filepath = os.path.join(temp_dir, temp_filename)

                formatted_start = format_duration(start_time)
                formatted_end = format_duration(end_time)

                # Configure twitch-dl options
                args = [
                    'twitch-dl', 'download',
                    '-q', '720p60',
                    '-s', formatted_start,
                    '-e', formatted_end,
                    '-f', '.mp4',
                    '-o', temp_filepath,
                    vod_id,
                ]

                if MODE == 'production' and user_id != 'n7wHc2evvDVlhlJHV29R1Px6Zgk1':
                    args += ['--auth-token', access_token]

                process = subprocess.Popen(args, stdout=True)
                process.wait()

                clips = process_video(temp_dir, input_file=temp_filepath)

            except ValueError as e:
                abort(400, str(e))

            uploaded_clips = upload_files_to_s3(
                clips,
                folder_path=f"{user_id}",
                file_prefix="twitch-"
            )

    return uploaded_clips
