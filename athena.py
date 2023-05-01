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
seconds_to_capture = 30
minimum_clips = 6
maximum_clips = 12


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
    # we spread out the interval to match seconds_to_capture

    # this states we are discovering db levels on this many second intervals
    seconds_to_discover = 1

    sample_rate, audio_data = wavfile.read(audio_file)
    audio_sample_count = audio_data.shape[0]
    samples_per_frame = sample_rate/frame_rate
    audio_frame_count = int(math.ceil(audio_sample_count/samples_per_frame))

    print('audio frame count', audio_frame_count)
    print('samples per frame', samples_per_frame)

    frame_audio_db_levels = []  # this stores frame by frame db levels
    highest_db_level = -100

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

    # we measure db levels on frame_intervals number of frames
    results = []
    current_frame = 0
    highest_interval_db_avg = -100
    total_db_intervals = 0
    total_intervals = 0

    frame_intervals = int(math.ceil(seconds_to_discover * frame_rate))

    # we need enough frames to fill out a total of seconds_to_capture
    frames_to_capture = int(math.ceil(
        (seconds_to_capture * frame_rate) - frame_intervals
    ) / 2)

    # get highest average amongst all intervals
    for i in range(0, audio_frame_count, frame_intervals):
        interval_end_frame = min(audio_frame_count, i + frame_intervals)

        # average of the current frame interval
        interval_db_avg = sum(
            frame_audio_db_levels[i:interval_end_frame]
        ) / frame_intervals

        highest_interval_db_avg = max(interval_db_avg, highest_interval_db_avg)

        total_db_intervals += interval_db_avg
        total_intervals += 1

    total_avg_intervals = (total_db_intervals / total_intervals)
    threshold = ((highest_interval_db_avg - total_avg_intervals) / 2) + \
        (highest_db_level - highest_interval_db_avg)

    print('The highest average db for an interval is', highest_interval_db_avg)
    print('The highest db for a single frame is', highest_db_level)
    print('Total average of all frame intervals', total_avg_intervals)
    print(
        f"Identifying frame intervals of {frame_intervals} to see which is the loudest"
    )

    while (not results or len(results) < minimum_clips):
        print('threshold is currently', threshold)

        for i in range(0, audio_frame_count, frame_intervals):
            if (i <= current_frame):
                continue

            exists_in_results = False

            for sublist in results:
                if sublist['interval'][0] == i:
                    exists_in_results = True

            if exists_in_results:
                continue

            interval_end_frame = min(audio_frame_count, i + frame_intervals)

            # average of the current frame interval
            db_level = sum(
                frame_audio_db_levels[i:interval_end_frame]
            ) / frame_intervals

            diff = db_level - total_avg_intervals

            # print(
            #     f"Frames {i} - {interval_end_frame} have a db level of {db_level}"
            # )

            if diff > threshold:
                print(
                    f"Frames {i} - {interval_end_frame} added as loud with db level of {db_level}"
                )
                # capture this amount of frames before and after current frame based on how many seconds
                capture_end = min(audio_frame_count, i + frames_to_capture)

                results.append({
                    'interval': [i, interval_end_frame],
                    'db_level': db_level
                })

                # update the loop starting index
                current_frame = capture_end

        threshold -= .1

    if (len(results) > maximum_clips):
        print(
            f"Too many results - retrieving the {maximum_clips} loudest frames")
        sorted_results = sorted(
            results, key=lambda obj: obj['db_level'], reverse=True)
        results = sorted_results[:maximum_clips]

    return results, frames_to_capture


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

        clip_frames = get_clip_frames(
            loud_frames,
            total_frames,
            frames_to_capture
        )

        cut_clips(input_file, clip_frames)


if __name__ == "__main__":
    main()
