from flask import  request, abort, jsonify
import tweepy
from config import TWITTER_API_KEY, TWITTER_API_SECRET

def twitter_auth():
    auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
    redirect_url = auth.get_authorization_url()
    return { 'redirect_url': redirect_url }, 200

def twitter_callback(oauth_token, oauth_verifier):
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

        # Store the access tokens in firestore


        return jsonify({
            'access_token': access_token,
            'access_token_secret': access_token_secret
        })
    
    except tweepy.errors.TweepyException as e:
        print(e)
        abort(500, e)
    


