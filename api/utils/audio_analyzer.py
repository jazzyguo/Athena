from scipy.io import wavfile
import math
import numpy as np
import librosa
from typing import List, Tuple, TypedDict


Frames = List[Tuple[int, int]]


CalculatedFrame = TypedDict(
    'CalculatedFrame', {'interval': Tuple[int, int], 'db_level': int}
)


def get_frames_to_clip(frames: Frames, total_frames: int, frames_to_capture_before: int, frames_to_capture_after: int) -> Frames:
    # return an array of arrays with frame [start,end] to get clips for
    results: Frames = []

    # append appropriate padding for frames so that we can reach desired clip length
    for frame_object in frames:
        interval: int = frame_object['interval']
        start_frame: int = interval[0]
        end_frame: int = interval[1]

        # max/min to never go out of bounds of video frames
        capture_start = max(0, start_frame - frames_to_capture_before)
        capture_end = min(total_frames, end_frame + frames_to_capture_after)

        if (capture_start != 0):
            results.append([capture_start, capture_end])

    return results


def get_db_levels_per_frame(audio_file: str, frame_rate: float) -> Tuple[List[int], float, int]:
    sample_rate, audio_data = wavfile.read(audio_file)
    audio_sample_count: int = audio_data.shape[0]
    samples_per_frame: float = sample_rate/frame_rate
    audio_frame_count: int = int(
        math.ceil(audio_sample_count/samples_per_frame)
    )

    print('audio frame count', audio_frame_count)
    print('samples per frame', samples_per_frame)

    # this stores frame by frame db levels
    frame_audio_db_levels: List[int] = []
    highest_db_level: float = -100

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

    return frame_audio_db_levels, highest_db_level, audio_frame_count


def get_max_db_avg_from_intervals(
        frame_intervals: int,
        total_frames: int,
        frame_audio_db_levels: List[int],
) -> Tuple[float, float]:
    # we measure db levels on frame_intervals number of frames
    highest_interval_db_avg: float = -100
    total_db_intervals: int = 0
    total_intervals: int = 0

    # get highest average amongst all intervals
    for i in range(0, total_frames, frame_intervals):
        interval_end_frame = min(total_frames, i + frame_intervals)

        # average of the current frame interval
        interval_db_avg = sum(
            frame_audio_db_levels[i:interval_end_frame]
        ) / frame_intervals

        highest_interval_db_avg = max(interval_db_avg, highest_interval_db_avg)

        total_db_intervals += interval_db_avg
        total_intervals += 1

    total_db_avg = (total_db_intervals / total_intervals)

    return highest_interval_db_avg, total_db_avg


def get_loud_frames(audio_file: str, frame_rate: int, **kwargs) -> Frames:
    # the goal is to measure intervals of above avg decibel levels
    # once we identify all intervals equal or above the threshold,
    # we spread out the interval to match seconds_to_capture
    seconds_to_capture: int = kwargs['seconds_to_capture']
    minimum_clips: int = kwargs['minimum_clips']
    maximum_clips: int = kwargs['maximum_clips']

    # this states we are discovering db levels on this many second intervals
    seconds_to_discover: int = 3

    (
        frame_audio_db_levels,
        highest_db_level,
        audio_frame_count
    ) = get_db_levels_per_frame(audio_file, frame_rate)

    # we measure db levels on frame_intervals number of frames
    results: List[CalculatedFrame] = []
    current_frame = 0

    frame_intervals = int(math.ceil(seconds_to_discover * frame_rate))

    frames_to_capture = int(math.ceil(
        (seconds_to_capture * frame_rate) - frame_intervals
    ) / 2)

    # capture more frames before than after (1.5x)
    frames_to_capture_after = int(math.ceil(frames_to_capture / 2))

    frames_to_capture_before = frames_to_capture + frames_to_capture_after

    highest_interval_db_avg, total_db_avg = get_max_db_avg_from_intervals(
        frame_intervals,
        audio_frame_count,
        frame_audio_db_levels,
    )

    threshold: float = ((highest_interval_db_avg - total_db_avg) / 2) + \
        (highest_db_level - highest_interval_db_avg)

    print('The highest average db for an interval is', highest_interval_db_avg)
    print('The highest db for a single frame is', highest_db_level)
    print('Total average of all frame intervals', total_db_avg)
    print(
        f"Identifying frame intervals of {frame_intervals} to see which is the loudest"
    )

    while ((not results or len(results) < minimum_clips) and threshold > 0):
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

            diff = db_level - total_db_avg

            # print(
            #     f"Frames {i} - {interval_end_frame} have a db level of {db_level}"
            # )

            if diff > threshold:
                print(
                    f"Frames {i} - {interval_end_frame} added as loud with db level of {db_level}"
                )

                # capture this amount of frames before and after current frame based on how many seconds
                capture_end = min(audio_frame_count, i + frames_to_capture_after)

                results.append({
                    'interval': [i, interval_end_frame],
                    'db_level': db_level
                })

                # update the loop starting index
                current_frame = capture_end

        threshold -= .1

    if (len(results) > maximum_clips):
        print(
            f"Too many results - retrieving the {maximum_clips} loudest frames"
        )
        sorted_results: Frames = sorted(
            results, key=lambda obj: obj['db_level'], reverse=True)
        results = sorted_results[:maximum_clips]

    frames_to_clip = get_frames_to_clip(
        results,
        audio_frame_count,
        frames_to_capture_before,
        frames_to_capture_after,
    )

    return frames_to_clip
