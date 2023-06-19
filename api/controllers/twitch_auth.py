# only getting the access tokens from twitch, the client will be updating the firestore doc.
def twitch_auth(code, redirect_uri):
    return { 'access_token': 'asd', 'refresh_token': 'asds' }, 200
