import subprocess
import tempfile
import ffmpeg
from fractions import Fraction
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
from audio_analyzer import get_loud_frames
from settings import input_file


def extract_audio(input_file, output_file):
    command = f"ffmpeg -i '{input_file}' -ab 160k -ac 2 -ar 44100 -vn {output_file}"
    subprocess.call(command, shell=True)


def get_frame_rate(input_file):
    probe = ffmpeg.probe(input_file)
    video_stream = next(
        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    frame_rate = video_stream['avg_frame_rate']
    total_frames = int(probe["streams"][0]["nb_frames"])
    return float(Fraction(frame_rate)), total_frames


def get_clip_frames(frames, total_frames, frames_to_capture):
    # return an array of arrays with frame [start,end] to get clips for
    results = []

    for frame_object in frames:
        interval = frame_object['interval']
        start_frame = interval[0]
        end_frame = interval[1]

        # max/min to never go out of bounds of video frames
        capture_start = max(0, start_frame - frames_to_capture)
        capture_end = min(total_frames, end_frame + frames_to_capture)

        if (capture_start != 0):
            results.append([capture_start, capture_end])

    return results


def cut_clips(input_file, clip_frames):
    video = VideoFileClip(input_file)

    for i, cut in enumerate(clip_frames):
        print('cutting frames', cut)
        start_frame, end_frame = cut
        output_file = f'clips/{os.path.splitext(input_file)[0]}_clip{i}.mp4'
        clip = video.subclip(start_frame/video.fps, end_frame/video.fps)
        clip.write_videofile(output_file)


def process_video():
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_output = f"{temp_dir}/audio.wav"

        extract_audio(input_file, audio_output)

        frame_rate, total_frames = get_frame_rate(input_file)

        print(f"Frame rate: {frame_rate}")

        loud_frames, frames_to_capture = get_loud_frames(
            audio_output,
            frame_rate
        )

        clip_frames = get_clip_frames(
            loud_frames,
            total_frames,
            frames_to_capture
        )

        cut_clips(input_file, clip_frames)


if __name__ == "__main__":
    process_video()
