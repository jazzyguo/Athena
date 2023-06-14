from flask import abort, request
from functools import wraps
from firebase_admin import auth

def auth_required(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]

            try:
                decoded_user = auth.verify_id_token(access_token)

                if decoded_user and 'uid' in decoded_user:
                    request.user_id = decoded_user['uid']
                    return fn(*args, **kwargs)
                else:
                    abort(401, 'Unauthorized')

            except auth.InvalidIdTokenError:
                abort(401, 'Unauthorized')


    return decorated
