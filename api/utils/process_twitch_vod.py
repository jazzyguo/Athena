import threading
from flask_socketio import SocketIO
from .. import create_app
from api.utils import process_video
import os
import time
import tempfile
import subprocess
import datetime
from api.firestore import db
from api.constants import MODE


app = create_app()
socketio = SocketIO(app)


def format_duration(duration_seconds):
    duration = datetime.timedelta(seconds=int(duration_seconds))
    return str(duration)

# vid files are saved in s3 in {user_id}/temp_clips/twitch-{vod_id}-{timestamp now}_frames-{start}to{end}.mp4


def process_vod(vod_id, start_time, end_time, user_id):
    # fetch twitch access token using user_id
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if user_doc.exists:
        access_token = user_doc.get('connections').get(
            'twitch').get('access_token')

        with tempfile.TemporaryDirectory() as temp_dir:
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

            process_video(
                temp_dir,
                input_file=temp_filepath,
                s3_folder_path=f"{user_id}",
                s3_file_prefix="twitch-"
            )


def process_twitch_vod_async(vod_id, start_time, end_time, user_id):
    def task():
        with app.app_context():
            process_vod(vod_id, start_time, end_time, user_id)
            socketio.emit(f'twitch_vod_processed_{user_id}')

    thread = threading.Thread(target=task)
    thread.start()


if __name__ == '__main__':
    socketio.run(app)
