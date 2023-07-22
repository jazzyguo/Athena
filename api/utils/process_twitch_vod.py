from api.s3.upload import upload_file_to_s3
from api.utils import get_loud_frames
import os
import time
import tempfile
import subprocess
import datetime
from api.firestore import db
from api.constants import MODE
from app import socketio
import gevent
from api.config import (
    default_seconds_to_capture,
    default_minimum_clips,
    default_maximum_clips
)
from .audio_analyzer import get_loud_frames, Frames
from .pad_interval import pad_interval
from typing import List
import math


def convert_mkv_to_wav(input_mkv_file, output_wav_file):
    subprocess.run(['ffmpeg', '-i', input_mkv_file, '-acodec',
                   'pcm_s16le', '-ar', '44100', output_wav_file])


def format_duration(duration_seconds):
    duration = datetime.timedelta(seconds=int(duration_seconds))
    return str(duration)

# vid files are saved in s3 in {user_id}/temp_clips/twitch-{vod_id}-{timestamp now}_frames-{start}to{end}.mp4


def process_twitch_vod_async(vod_id, start_time, end_time, user_id):
    def task():
        print('Twich vod process task started', flush=True)
        twitch_vod_processing(vod_id, start_time, end_time, user_id)
        socketio.emit(f'twitch_vod_processed_{user_id}')

    gevent.spawn(task)


def twitch_vod_processing(vod_id, start_time, end_time, user_id):
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if user_doc.exists:
        access_token = user_doc.get('connections').get(
            'twitch').get('access_token')

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                temp_filename = f'{vod_id}-{int(time.time())}'

                audio_output = os.path.join(temp_dir, temp_filename)

                formatted_start = format_duration(start_time)
                formatted_end = format_duration(end_time)

                # Configure twitch-dl options
                args = [
                    'twitch-dl', 'download',
                    '-q', 'audio_only',
                    '-s', formatted_start,
                    '-e', formatted_end,
                    '-o', f'{audio_output}.mkv',
                    vod_id,
                    '--overwrite',
                ]

                if MODE == 'production' and user_id != 'n7wHc2evvDVlhlJHV29R1Px6Zgk1':
                    args += ['--auth-token', access_token]

                process = subprocess.Popen(args, stdout=True)
                process.wait()

                audio_output_wav = f'{audio_output}.wav'

                convert_mkv_to_wav(f'{audio_output}.mkv', audio_output_wav)

                s3_folder_path = user_id
                s3_file_prefix = "twitch-"

                frames_to_clip: Frames = get_loud_frames(
                    audio_output_wav,
                    60,
                    seconds_to_capture=default_seconds_to_capture,
                    maximum_clips=default_maximum_clips,
                    minimum_clips=default_minimum_clips,
                )

                make_clips(
                    vod_id,
                    audio_output_wav,
                    temp_dir,
                    frames_to_clip,
                    s3_folder_path,
                    s3_file_prefix,
                    user_id,
                    access_token,
                )
            except ValueError as e:
                print(f'Error twitch vod processing {e}', flush=True)
    else:
        raise Exception('No user document existing')


# uses twitch-dl to download the clips created from audio_analyzer
def make_clips(
        vod_id: str,
        audio_output_wav: str,
        temp_dir: str,
        frames_to_clip: Frames,
        s3_folder_path: str,
        s3_file_prefix: str,
        user_id: str,
        access_token: str,
) -> List[str]:
    results = []

    for i, frames in enumerate(frames_to_clip):
        start_frame, end_frame = frames

        try:
            clip = make_clip(
                vod_id,
                audio_output_wav,
                temp_dir,
                s3_folder_path,
                s3_file_prefix,
                start_frame,
                end_frame,
                i,
                user_id,
                access_token,
            )
            results.append(clip)
        except Exception as exc:
            print(f"Error creating clip for clip {i+1} - {exc}")

    return results


def make_clip(
    vod_id: str,
    audio_output_wav: str,
    temp_dir: str,
    s3_folder_path: str,
    s3_file_prefix: str,
    start_frame: int,
    end_frame: int,
    clip_number: int,
    user_id: str,
    access_token: str,
) -> str:
    # start_time / end_time is calculated using an assumed frame_rate of 60fps and the frame

    start_time = int(math.ceil(start_frame / 60) - 5)
    end_time = int(math.ceil(end_frame / 60) - 5)

    # twitch-dl always adds 10s to the clip downloaded for some reason
    padded_start_time, padded_end_time = pad_interval(
        start_time,
        end_time,
        target_seconds=20
    )

    formatted_start = format_duration(padded_start_time)
    formatted_end = format_duration(padded_end_time)

    path = audio_output_wav
    filename = os.path.basename(path)
    name = os.path.splitext(filename)[0]
    output_file_path = f'{temp_dir}/{name}__timestamp-{padded_start_time}to{padded_end_time+10}.mp4'

    # Configure twitch-dl options
    args = [
        'twitch-dl', 'download',
        '-q', '720p60',
        '-s', formatted_start,
        '-e', formatted_end,
        '-f', '.mp4',
        '-o', output_file_path,
        vod_id,
    ]

    if MODE == 'production' and user_id != 'n7wHc2evvDVlhlJHV29R1Px6Zgk1':
        args += ['--auth-token', access_token]

    process = subprocess.Popen(args, stdout=True)
    process.wait()

    print(
        f'Starting to clip {clip_number+1} - frames {[formatted_start, formatted_end]}...', flush=True
    )
    print(f'Clip {clip_number+1} written and now uploading to s3', flush=True)

    uploaded_file = upload_file_to_s3(
        s3_folder_path,
        output_file_path,
        s3_file_prefix,
    )

    print(f'Clip {clip_number+1} uploaded successfully', flush=True)

    # s3_folder_path is just the user_id
    socketio.emit(
        f'clip_generated_{s3_folder_path}', uploaded_file
    )

    os.remove(output_file_path)

    return uploaded_file
