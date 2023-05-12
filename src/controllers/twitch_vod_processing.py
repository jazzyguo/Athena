from flask import request, abort, jsonify
from athena import process_video
from s3_upload import upload_files_to_s3
import os
import time
import tempfile
import subprocess
import datetime


def format_duration(duration_seconds):
    duration = datetime.timedelta(seconds=int(duration_seconds))
    return str(duration)


def twitch_vod_processing(vod_id):
    max_length = 3600  # time in sec of max length

    payload = request.json

    access_token = request.headers.get('Authorization')
    start_time: str = payload.get('start')  # in seconds
    end_time: str = payload.get('end')
    user_id = payload.get('user_id')

    start = int(start_time.rstrip("0").rstrip("."))
    end = int(end_time.rstrip("0").rstrip("."))

    if user_id is None:
        abort(401, 'Access Denied')

    if start is None or end is None:
        abort(400, 'Required timestamps are missing')

    # calculate the time difference
    time_diff = end - start

    if (time_diff > max_length or start >= end):
        abort(400, 'Bad timestamps')

    clips = []
    uploaded_clips = []

    # sse.publish(
    #     'Video is currently being processed...',
    #     channel='status'
    # )

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            temp_filename = f'{vod_id}-{int(time.time())}.mp4'

            temp_filepath = os.path.join(temp_dir, temp_filename)

            formatted_start = format_duration(start)
            formatted_end = format_duration(end)

            # Configure twitch-dl options
            args = ['twitch-dl', 'download', '-q', '720p60', '-s', formatted_start, '-e', formatted_end,
                    '-f', '.mp4', '-o', temp_filepath, vod_id]

            process = subprocess.Popen(args, stdout=True)
            process.wait()

            # sse.publish(
            #     'Clips are currently being generated...',
            #     channel='status'
            # )

            clips = process_video(temp_dir, input_file=temp_filepath)

        except ValueError as e:
            abort(400, str(e))

        uploaded_clips = upload_files_to_s3(
            clips, folder_path=f"{user_id}/temp_clips", file_prefix="twitch-")

    response = jsonify({
        'urls': uploaded_clips
    })

    return response, 200
