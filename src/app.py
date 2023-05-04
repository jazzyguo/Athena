from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from athena import process_video
from s3_upload import upload_files_to_s3
import os
import time
from typing import BinaryIO

app = Flask(__name__)

CORS(app)


@app.route('/')
def index():
    return ''


@app.route('/process_video', methods=['POST'])
def process_file():

    uploaded_video: BinaryIO = request.files['videoFile']

    file_extension: str = os.path.splitext(uploaded_video.filename)[1]
    temp_filename = f'{int(time.time())}{file_extension}'
    temp_filepath = os.path.join('/tmp', temp_filename)

    if uploaded_video is None:
        abort(400, 'Required video file is missing')

    uploaded_video.save(temp_filepath)

    clips = []

    try:
        clips = process_video(input_file=temp_filepath)
    except ValueError as e:
        os.remove(temp_filepath)
        abort(400, str(e))

    os.remove(temp_filepath)

    uploaded_clips = upload_files_to_s3(clips)
    list(map(os.remove, clips))

    response = jsonify({
        'urls': uploaded_clips
    })

    return response, 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
