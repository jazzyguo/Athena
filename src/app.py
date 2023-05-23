from flask import Flask, abort, request
from flask_cors import CORS
from controllers.file_processing import process_file
from controllers.twitch_vod_processing import twitch_vod_processing
from controllers.clips import get_saved_clips, get_temp_clips, save_clip, delete_clip
from controllers.twitter import twitter_auth, twitter_callback
from typing import BinaryIO

app = Flask(__name__)

CORS(app)


@app.route('/')
def index():
    return ''


@app.route('/process_file', methods=['POST'])
def process_file_route():
    user_id = request.form.get('user_id')
    uploaded_video: BinaryIO = request.files['videoFile']

    return process_file(user_id, uploaded_video)


@app.route('/twitch/process_vod/<vod_id>', methods=['POST'])
def twitch_vod_processing_route(vod_id):
    payload = request.json
    max_length = 3600  # time in sec of max length

    if payload:
        access_token = request.headers.get('Authorization')
        start_time: int = payload.get('start')  # in seconds
        end_time: int = payload.get('end')
        user_id = payload.get('user_id')

        if user_id is None:
            abort(401, 'Access Denied')

        if start_time is None or end_time is None:
            abort(400, 'Required timestamps are missing')

        # calculate the time difference
        time_diff = end_time - start_time

        if (time_diff > max_length or start_time >= end_time):
            abort(400, 'Bad timestamps')

        return twitch_vod_processing(vod_id, access_token, start_time, end_time, user_id)
    else:
        abort(400, 'Params missing')


@app.route('/clips/saved')
def get_saved_clips_route():
    user_id = request.args.get('user_id')

    if user_id is None:
        abort(401, 'Access Denied')

    return get_saved_clips(user_id)


@app.route('/clips/temporary')
def get_temp_clips_route():
    user_id = request.args.get('user_id')

    if user_id is None:
        abort(401, 'Access Denied')

    return get_temp_clips(user_id)


@app.route('/clips/save', methods=['POST'])
def save_clip_route():
    payload = request.json

    if payload:
        user_id: str = payload.get('user_id')
        s3_key: str = payload.get('s3_key')

        if user_id is None:
            abort(401, 'Access Denied')

        return save_clip(user_id, s3_key)
    else:
        abort(400, 'Params missing')


@app.route('/clips/save', methods=['DELETE'])
def delete_clip_route():
    payload = request.json

    if payload:
        user_id: str = payload.get('user_id')
        s3_key: str = payload.get('s3_key')

        if user_id is None:
            abort(401, 'Access Denied')

        return delete_clip(user_id, s3_key)
    else:
        abort(400, 'Params missing')

@app.route('/connect/twitter/auth')
def twitter_connect_auth_route():
    return twitter_auth()

@app.route('/connect/twitter/callback')
def twitter_callback_route():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    return twitter_callback(oauth_token, oauth_verifier)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')