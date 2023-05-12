from flask import request

# in firestore, we will have keys of all clips saved/published by the user


def get_saved_clips():
    user_id = request.args.get('user_id')
    return [user_id]

# in s3, we can check the {bucket}/{user_id}/temp_clips folder
# and return signed urls of all the files


def get_temp_clips():
    user_id = request.args.get('user_id')
    return [user_id]
