from flask import abort, jsonify
import tweepy
from config import TWITTER_API_KEY, TWITTER_API_SECRET
from firestore_client import db

def twitter_auth():
    auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
    redirect_url = auth.get_authorization_url()
    return { 'redirect_url': redirect_url }, 200


def twitter_callback(oauth_token, oauth_verifier, user_id):
    # Set up the OAuth handler with the request token
    auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)

    auth.request_token = {
        'oauth_token': oauth_token, 
        'oauth_token_secret': oauth_verifier,
    }

    try:
        # Exchange the request token for access tokens
        auth.get_access_token(oauth_verifier)

        # Get the access tokens
        access_token = auth.access_token
        access_token_secret = auth.access_token_secret

        # Fetch the Twitter profile and email associated with the token
        api = tweepy.API(auth)
        user = api.verify_credentials()

        screen_name = user.screen_name

        twitter_info = {
            'access_token': access_token,
            'access_token_secret': access_token_secret,
            'screen_name': screen_name,
        }

        # Update the Firestore document with the profile information
        doc_ref = db.collection('users').document(user_id)
        doc_ref.update({
            'connections.twitter': twitter_info
        })

        return jsonify(twitter_info)
    
    except tweepy.errors.TweepyException as e:
        print(e)
        abort(500, e)
    

def twitter_auth_delete(user_id):
    # Retrieve the access tokens from Firestore
    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()
    
    if doc.exists:
        connections = doc.get('connections')
        if 'twitter' in connections:
            # Delete the access tokens from Firestore
            del connections['twitter']
            doc_ref.update({'connections': connections})

            return 'Success', 200
        else:
            # Handle the case when the Twitter connection does not exist
            raise Exception('Twitter connection not found for the user')
    else:
        # Handle the case when the user document does not exist
        raise Exception('User not found')

