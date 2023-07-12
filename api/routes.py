from flask import abort, request
from typing import BinaryIO
from .middleware import auth_required
from .controllers import (
    process_file,
    get_saved_clips,
    get_temp_clips,
    save_clip,
    delete_clip,
    twitter_auth,
    twitter_callback,
    twitter_auth_delete,
    twitch_auth,
    clips_publish_twitter
)
from .utils import process_twitch_vod_async
from app import app


@app.route('/')
def index():
    return ''


@app.route('/process_file', methods=['POST'])
@auth_required
def process_file_route():
    user_id = request.user_id
    uploaded_video: BinaryIO = request.files['videoFile']

    return process_file(user_id, uploaded_video)


@app.route('/twitch/process_vod/<vod_id>', methods=['POST'])
@auth_required
def twitch_vod_processing_route(vod_id):
    user_id = request.user_id
    payload = request.json
    max_length = 3600  # time in sec of max length

    if payload:
        start_time: int = payload.get('start')  # in seconds
        end_time: int = payload.get('end')

        if start_time is None or end_time is None:
            abort(400, 'Required timestamps are missing')

        # calculate the time difference
        time_diff = end_time - start_time

        if (time_diff > max_length or start_time >= end_time):
            abort(400, 'Bad timestamps')

        try:
            process_twitch_vod_async(
                vod_id,
                start_time,
                end_time,
                user_id,
            )
        except ValueError as e:
            abort(400, str(e))

        return {
            'message': 'Vod processing received'
        }, 200
    else:
        abort(400, 'Params missing')


# CLIPS ROUTES
@app.route('/clips/saved')
@auth_required
def get_saved_clips_route():
    user_id = request.user_id
    return get_saved_clips(user_id)


@app.route('/clips/temporary')
@auth_required
def get_temp_clips_route():
    user_id = request.user_id
    return get_temp_clips(user_id)


@app.route('/clips/save', methods=['POST'])
@auth_required
def save_clip_route():
    payload = request.json
    user_id = request.user_id

    if payload:
        s3_key: str = payload.get('s3_key')

        if s3_key is None:
            abort(400, 'Required s3 key missing')

        return save_clip(user_id, s3_key)
    else:
        abort(400, 'Params missing')


@app.route('/clips/save', methods=['DELETE'])
@auth_required
def delete_clip_route():
    user_id = request.user_id
    s3_key = request.args.get('s3_key')

    if s3_key is None:
        abort(400, 'Required s3 key missing')

    return delete_clip(user_id, s3_key)


# PUBLISH ROUTES
@app.route('/clips/publish/twitter', methods=['POST'])
@auth_required
def clips_publish_twitter_route():
    user_id = request.user_id
    clip_url = request.form.get('clip_url')
    content = request.form.get('text')

    return clips_publish_twitter(user_id, content, clip_url)


# CONNECT ROUTES
@app.route('/connect/twitter/auth')
@auth_required
def twitter_connect_auth_route():
    return twitter_auth()


@app.route('/connect/twitter/auth', methods=['DELETE'])
@auth_required
def twitter_connect_auth_delete_route():
    user_id = request.user_id
    return twitter_auth_delete(user_id)


@app.route('/connect/twitter/callback')
@auth_required
def twitter_callback_route():
    user_id = request.user_id
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    return twitter_callback(oauth_token, oauth_verifier, user_id)


@app.route('/connect/twitch/auth', methods=['POST'])
@auth_required
def twitch_connect_auth_route():
    payload = request.json

    if payload:
        redirect_uri: str = payload.get('redirect_uri')
        code: str = payload.get('code')

        return twitch_auth(code, redirect_uri)
    else:
        abort(400, 'Params missing')
