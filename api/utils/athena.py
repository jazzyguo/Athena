import subprocess
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
import concurrent.futures
from typing import List, BinaryIO
from api.s3 import upload_file_to_s3

from .audio_analyzer import get_loud_frames, Frames
from api.config import (
    default_seconds_to_capture,
    default_minimum_clips,
    default_maximum_clips
)


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
) -> str:
    print(
        f'Starting to clip {clip_number} - frames {[start_frame, end_frame]}...')
    video = VideoFileClip(input_file)
    path = input_file
    filename = os.path.basename(path)
    name = os.path.splitext(filename)[0]
    output_file_path = f'{temp_dir}/{name}__frames-{start_frame}to{end_frame}.mp4'
    clip = video.subclip(start_frame / video.fps, end_frame / video.fps)
    clip.write_videofile(output_file_path)

    uploaded_file = upload_file_to_s3(
        s3_folder_path,
        output_file_path,
        s3_file_prefix,
    )

    os.remove(output_file_path)

    return uploaded_file


def make_clips(
        input_file: str,
        temp_dir: str,
        frames_to_clip: Frames,
        s3_folder_path: str,
        s3_file_prefix: str
) -> List[str]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for i, frames in enumerate(frames_to_clip):
            start_frame, end_frame = frames
            futures.append(executor.submit(
                make_clip,
                input_file,
                temp_dir,
                s3_folder_path,
                s3_file_prefix,
                start_frame,
                end_frame,
                i
            ))

        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                print(f"Error creating clip for clip {i} - {exc}")
            else:
                results.append(result)

    return results


def process_video(temp_dir, **kwargs) -> List[str]:
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

    print(f"Frame rate: {frame_rate}")

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
        )
    except Exception as e:
        print(f"Error generating clips: {e}")

    return clips
