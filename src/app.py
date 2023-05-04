from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from athena import process_video
from s3_upload import upload_files_to_s3
import os
import time
import tempfile
from typing import BinaryIO

app = Flask(__name__)

CORS(app)


@app.route('/')
def index():
    return ''


@app.route('/process_video', methods=['POST'])
def process_file():

    uploaded_video: BinaryIO = request.files['videoFile']

    filename, file_extension = os.path.splitext(uploaded_video.filename)

    temp_filename = f'{filename}-{int(time.time())}{file_extension}'

    if uploaded_video is None:
        abort(400, 'Required video file is missing')

    clips = []
    uploaded_clips = []

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            temp_filepath = os.path.join(temp_dir, temp_filename)
            uploaded_video.save(temp_filepath)

            clips = process_video(temp_dir, input_file=temp_filepath)
        except ValueError as e:
            abort(400, str(e))

        uploaded_clips = upload_files_to_s3(clips)

    response = jsonify({
        'urls': uploaded_clips
    })

    return response, 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
