import subprocess
import tempfile
import ffmpeg
from scipy.io import wavfile
import math
from fractions import Fraction
import numpy as np
import librosa
import os
from moviepy.video.io.VideoFileClip import VideoFileClip

# number of s before and after
seconds_to_capture = 15


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


def get_loud_frames(audio_file, frame_rate):
    # the goal is to measure intervals of above avg decibel levels
    # once we identify all intervals equal or above the threshold,
    # we spread out the interval to match seconds_to_capture * 2

    sample_rate, audio_data = wavfile.read(audio_file)
    audio_sample_count = audio_data.shape[0]
    samples_per_frame = sample_rate/frame_rate
    audio_frame_count = int(math.ceil(audio_sample_count/samples_per_frame))

    print('audio frame count', audio_frame_count)
    print('samples per frame', samples_per_frame)

    frame_audio_db_levels = []  # this stores frame by frame db levels
    highest_db_level = -100
    highest_db_frame = 0
    total_db_level = 0

    # calc highest db level and get db levels for each audio chunk on a frame by frame basis
    for i in range(audio_frame_count):
        start = int(i*samples_per_frame)
        end = min(int((i+1)*samples_per_frame), audio_sample_count)
        audio_chunk = audio_data[start:end]
        rms = np.sqrt(np.mean(np.square(audio_chunk)))
        db_level = librosa.power_to_db(rms, ref=1.0)
        if math.isnan(db_level):
            db_level = 0
        frame_audio_db_levels.append(db_level)
        highest_db_level = max(highest_db_level, db_level)
        highest_db_frame = max(highest_db_frame, i)
        total_db_level += db_level

    avg_db_level = (total_db_level / audio_frame_count)
    threshold = ((highest_db_level - avg_db_level) / 2)

    print('threshold', threshold)
    print('highest_db_level', highest_db_level)
    print('avg_db_level', avg_db_level)

    # we measure db levels on frame_intervals number of frames
    results = []
    current_frame = 0

    frame_intervals = int(math.ceil(seconds_to_capture / 2) * frame_rate)

    # if frame intervals of x we need enough frames to fill out a total of seconds_to_capture * 2
    frames_to_capture = int(math.ceil(
        (seconds_to_capture * 2 * frame_rate) - frame_intervals
    ) / 2)

    for i in range(0, audio_frame_count, frame_intervals):
        if (i <= current_frame):
            continue

        interval_end_frame = min(audio_frame_count, i + frame_intervals)

        # average of the current frame interval
        db_level = sum(
            frame_audio_db_levels[i:interval_end_frame]
        ) / frame_intervals

        diff = db_level - avg_db_level

        if diff > threshold:
            print(
                f"Frames {i} - {interval_end_frame} added as loud with db level of {db_level}"
            )
            # capture this amount of frames before and after current frame based on how many seconds
            capture_end = min(audio_frame_count, i + frames_to_capture)

            results.append([i, interval_end_frame])

            # update the loop starting index
            current_frame = capture_end

    # default clip of highest db
    if not results:
        print('no frames found, appending highest db frame')
        results.append([
            highest_db_frame, min(
                audio_frame_count, highest_db_frame+frames_to_capture
            )
        ])

    return results, frames_to_capture


def get_clip_frames(frames, total_frames, frames_to_capture):
    # return an array of arrays with frame [start,end] to get clips for
    results = []

    for start_frame, end_frame in frames:
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


def main():
    input_file = 'nba.mp4'

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_output = f"{temp_dir}/audio.wav"

        extract_audio(input_file, audio_output)

        frame_rate, total_frames = get_frame_rate(input_file)

        print(f"Frame rate: {frame_rate}")

        loud_frames, frames_to_capture = get_loud_frames(
            audio_output,
            frame_rate
        )

        print(loud_frames)

        clip_frames = get_clip_frames(
            loud_frames,
            total_frames,
            frames_to_capture
        )

        cut_clips(input_file, clip_frames)


if __name__ == "__main__":
    main()
