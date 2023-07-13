from flask import abort
from api.utils import process_twitch_vod_async


def twitch_vod_processing(vod_id, start_time, end_time, user_id):
    try:
        process_twitch_vod_async(
            vod_id,
            start_time,
            end_time,
            user_id,
        )
    except Exception as e:
        print('Processing twitch vod error', e)
        abort(500)
