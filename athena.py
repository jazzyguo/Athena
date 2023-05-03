import subprocess
import tempfile
import ffmpeg
from fractions import Fraction
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
import concurrent.futures
from typing import List
from audio_analyzer import get_loud_frames
from typings import Frames
from settings import (
    input_file,
    default_seconds_to_capture,
    default_minimum_clips,
    default_maximum_clips
)


def extract_audio(input_file: str, output_file: str) -> None:
    command = f"ffmpeg -i '{input_file}' -ab 160k -ac 2 -ar 44100 -vn {output_file}"
    subprocess.call(command, shell=True)


def get_frame_rate(input_file: str) -> float:
    probe = ffmpeg.probe(input_file)
    video_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    frame_rate = video_stream['avg_frame_rate']
    return float(Fraction(frame_rate))


def make_clip(input_file: str, start_frame: int, end_frame: int, clip_number: int) -> str:
    print(
        f'Starting to clip {clip_number} - frames {[start_frame, end_frame]}...')
    video = VideoFileClip(input_file)
    output_file = f'clips/{os.path.splitext(input_file)[0]}_clip{clip_number}.mp4'
    clip = video.subclip(start_frame / video.fps, end_frame / video.fps)
    clip.write_videofile(output_file)
    return output_file


def make_clips(input_file: str, frames_to_clip: Frames) -> List[str]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i, frames in enumerate(frames_to_clip):
            start_frame, end_frame = frames
            futures.append(executor.submit(
                make_clip,
                input_file,
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


def process_video(**kwargs) -> List[str]:
    seconds_to_capture: int = kwargs.get(
        'seconds_to_capture', default_seconds_to_capture
    )
    minimum_clips: int = kwargs.get('minimum_clips', default_minimum_clips)
    maximum_clips: int = kwargs.get('maximum_clips', default_maximum_clips)

    if minimum_clips >= maximum_clips:
        raise ValueError('Minimum must be less than maximum.')

    with tempfile.TemporaryDirectory() as temp_dir:
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
            clips = make_clips(input_file, frames_to_clip)
        except Exception as e:
            print(f"Error generating clips: {e}")

    return clips


if __name__ == "__main__":
    process_video()
