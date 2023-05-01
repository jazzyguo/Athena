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

temp_dir = "temp"

# number of s before and after
seconds_to_capture = 15

def extract_frames(input_file, output_file):
    command = f"ffmpeg -i '{input_file}' -vf scale=1920:1080 {output_file} -hide_banner"
    subprocess.call(command, shell=True)


def extract_audio(input_file, output_file):
    command = f"ffmpeg -i '{input_file}' -ab 160k -ac 2 -ar 44100 -vn {output_file}"
    subprocess.call(command, shell=True)

def get_frame_rate(input_file):
    probe = ffmpeg.probe(input_file)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    frame_rate = video_stream['avg_frame_rate']
    total_frames = int(probe["streams"][0]["nb_frames"])
    return float(Fraction(frame_rate)), total_frames


def get_loud_frames(audio_file, frame_rate):
    sample_rate, audio_data = wavfile.read(audio_file)

    audio_sample_count = audio_data.shape[0]

    samples_per_frame = sample_rate/frame_rate

    audio_frame_count = int(math.ceil(audio_sample_count/samples_per_frame))

    avg_db_level = librosa.power_to_db(np.sqrt(np.mean(np.square(audio_data))), ref=1.0)

    print('average db level', avg_db_level)
    print('audio frame count', audio_frame_count)

    results = []
    current_frame = 0
    audio_chunk_db_levels = []
    highest_db_level = -100

    # calc highest db level and get db levels for each audio chunk
    for i in range(audio_frame_count):
        start = int(i*samples_per_frame)
        end = min(int((i+1)*samples_per_frame),audio_sample_count)
        audio_chunk = audio_data[start:end]
        rms = np.sqrt(np.mean(np.square(audio_chunk)))
        db_level = librosa.power_to_db(rms, ref=1.0)
        audio_chunk_db_levels.append(db_level)
        highest_db_level = max(highest_db_level, db_level)

    threshold = (highest_db_level - avg_db_level) / 2

    print('threshold', threshold)
    print('highest_db_level', highest_db_level)
    print('avg_db_level', avg_db_level)

    for i in range(audio_frame_count):
        if(i <= current_frame):
            continue
            
        db_level = audio_chunk_db_levels[i]
        diff = db_level - avg_db_level

        if diff > threshold:
            print(f"Frame {i} added as loud frame with db level of {db_level}")
            # capture this amount of frames before and after current frame based on how many seconds 
            frames_to_capture = math.ceil(seconds_to_capture * frame_rate)
            capture_end = min(audio_frame_count, i + frames_to_capture)

            results.append(i)
            
            # update the loop starting index
            current_frame = capture_end

    return results

# based on number array of frames,
# return an array of arrays with frame [start,end] to get clips for
def get_clip_frames(frames, frame_rate, total_frames):
    results = []
    for frame in frames:
        # capture this amount of frames before and after current frame based on how many seconds 
        frames_to_capture = math.ceil(seconds_to_capture * frame_rate)

        # max/min to never go out of bounds of video frames
        capture_start = max(0, frame - frames_to_capture)
        capture_end = min(total_frames, frame + frames_to_capture)
        
        if(capture_start != 0):
            results.append([capture_start, capture_end])

    return results

def cut_clips(input_file, clip_frames):
    video = VideoFileClip(input_file)

    for i, cut in enumerate(clip_frames):
        print(cut)
        start_frame, end_frame = cut
        output_file  = f'clips/{os.path.splitext(input_file)[0]}_clip{i}.mp4'
        clip = video.subclip(start_frame/video.fps, end_frame/video.fps)
        clip.write_videofile(output_file)


def main():
    input_file = 'Beast.mp4'

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_output = f"{temp_dir}/audio.wav"

        extract_audio(input_file, audio_output)

        frame_rate, total_frames = get_frame_rate(input_file)

        print(f"Frame rate: {frame_rate}")

        loud_frames = get_loud_frames(audio_output, frame_rate)

        clip_frames = get_clip_frames(loud_frames, frame_rate, total_frames)

        cut_clips(input_file, clip_frames)


if __name__ == "__main__":
    main()
