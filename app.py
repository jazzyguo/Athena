from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from athena import process_video
import sys
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

    print(f'Video uploaded - {uploaded_video}')
    sys.stdout.flush()

    uploaded_video.save(temp_filepath)

    clips = []

    try:
        clips = process_video(input_file=temp_filepath)
    except ValueError as e:
        os.remove(temp_filepath)
        abort(400, str(e))

    response = {
        'clips': clips,
        'status': 'success',
        'message': 'The request was successful!'
    }

    os.remove(temp_filepath)

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
