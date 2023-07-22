import subprocess
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
from typing import List, BinaryIO
from api.s3 import upload_file_to_s3
from app import socketio
from .audio_analyzer import get_loud_frames, Frames
from api.config import (
    default_seconds_to_capture,
    default_minimum_clips,
    default_maximum_clips
)
import math
from .pad_interval import pad_interval


def extract_audio(input_file: str, output_file: str) -> None:
    command = f"ffmpeg -i '{input_file}' -ab 160k -ac 2 -ar 44100 -vn {output_file}"
    subprocess.call(command, shell=True)


def get_frame_rate(input_file: str) -> float:
    ffprobe_command = f"ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of default=noprint_wrappers=1:nokey=1 '{input_file}'"
    ffprobe_output = subprocess.check_output(
        ffprobe_command, shell=True).decode().strip()

    frame_rate = eval(ffprobe_output)
    return frame_rate


def make_clip(
        input_file: str,
        temp_dir: str,
        s3_folder_path: str,
        s3_file_prefix: str,
        start_frame: int,
        end_frame: int,
        clip_number: int,
        frame_rate: float,
) -> str:
    start_time = int(math.ceil(start_frame / frame_rate))
    end_time = int(math.ceil(end_frame / frame_rate))

    padded_start_time, padded_end_time = pad_interval(
        start_time,
        end_time,
    )

    print(
        f'Starting to clip {clip_number+1} - time {[padded_start_time, padded_end_time]}...', flush=True
    )

    video = VideoFileClip(input_file)
    path = input_file
    filename = os.path.basename(path)
    name = os.path.splitext(filename)[0]
    output_file_path = f'{temp_dir}/{name}____timestamp-{padded_start_time}to{padded_end_time}.mp4'
    clip = video.subclip(start_frame / video.fps, end_frame / video.fps)
    clip.write_videofile(
        output_file_path,
        verbose=False,
        logger=None,
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


def make_clips(
        input_file: str,
        temp_dir: str,
        frames_to_clip: Frames,
        s3_folder_path: str,
        s3_file_prefix: str,
        frame_rate: float,
) -> List[str]:
    results = []

    for i, frames in enumerate(frames_to_clip):
        start_frame, end_frame = frames

        try:
            clip = make_clip(
                input_file,
                temp_dir,
                s3_folder_path,
                s3_file_prefix,
                start_frame,
                end_frame,
                i,
                frame_rate,
            )
            results.append(clip)
        except Exception as exc:
            print(f"Error creating clip for clip {i} - {exc}")

    return results


def process_video_file(temp_dir, **kwargs) -> List[str]:
    print('Video processing started', flush=True)
    seconds_to_capture: int = kwargs.get(
        'seconds_to_capture', default_seconds_to_capture
    )
    minimum_clips: int = kwargs.get('minimum_clips', default_minimum_clips)
    maximum_clips: int = kwargs.get('maximum_clips', default_maximum_clips)
    input_file: BinaryIO = kwargs.get('input_file')
    s3_folder_path = kwargs.get('s3_folder_path')
    s3_file_prefix = kwargs.get('s3_file_prefix', '')

    if minimum_clips >= maximum_clips:
        raise ValueError('Minimum must be less than maximum.')

    audio_output: str = f"{temp_dir}/audio.wav"

    extract_audio(input_file, audio_output)

    frame_rate = get_frame_rate(input_file)

    print(f"Frame rate: {frame_rate}", flush=True)

    frames_to_clip: Frames = get_loud_frames(
        audio_output,
        frame_rate,
        seconds_to_capture=seconds_to_capture,
        maximum_clips=maximum_clips,
        minimum_clips=minimum_clips,
    )

    try:
        clips = make_clips(
            input_file,
            temp_dir,
            frames_to_clip,
            s3_folder_path,
            s3_file_prefix,
            frame_rate,
        )
    except Exception as e:
        print(f"Error generating clips: {e}")

    return clips
