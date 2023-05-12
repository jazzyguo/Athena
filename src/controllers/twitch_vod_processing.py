from flask import request, abort, jsonify
from athena import process_video
from s3_upload import upload_files_to_s3
import os
import time
import tempfile
import subprocess
import datetime


def twitch_vod_processing(vod_id):
    max_length = 3600  # time in sec of max length

    payload = request.json

    access_token = request.headers.get('Authorization')
    start_time = payload.get('start')
    end_time = payload.get('end')
    user_id = payload.get('user_id')

    if user_id is None:
        abort(401, 'Access Denied')

    if start_time is None or end_time is None:
        abort(400, 'Required timestamps are missing')

    # calculate the time difference
    dt_start = datetime.datetime.strptime(start_time, '%H:%M:%S')
    dt_end = datetime.datetime.strptime(end_time, '%H:%M:%S')

    time_diff = dt_end - dt_start

    if (time_diff.total_seconds() > max_length or dt_start >= dt_end):
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

            # Configure twitch-dl options
            args = ['twitch-dl', 'download', '-q', '720p60', '-s', start_time, '-e', end_time,
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

        uploaded_clips = upload_files_to_s3(clips, user_id=user_id)

    response = jsonify({
        'urls': uploaded_clips
    })

    return response, 200
