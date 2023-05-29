from flask import abort, jsonify
import tweepy
from config import TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_BEARER_TOKEN
from firestore_client import db
import requests
from io import BytesIO
from firestore_client import db
from controllers.clips import save_clip
import datetime


def authenticate_twitter_v2_api(access_token, access_token_secret):
    api = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        access_token=access_token,
        access_token_secret=access_token_secret,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
    )
    return api


def clips_publish_twitter(user_id, content, s3_key):
    # Fetch Twitter access tokens from Firestore using user_id
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            access_token = user_doc.get('connections').get('twitter').get('access_token')
            access_token_secret = user_doc.get('connections').get('twitter').get('access_token_secret')
            screen_name = user_doc.get('connections').get('twitter').get('screen_name')

            saved_clip = save_clip(user_id, s3_key)
            media_url = saved_clip['url']

            # Authenticate with Twitter API using the access tokens
            auth = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY, 
                TWITTER_API_SECRET, 
                access_token, 
                access_token_secret
            )

            api = tweepy.API(auth)

            try:
                media_response = requests.get(media_url)
                file_content = media_response.content

                file_obj = BytesIO(file_content)
                filename = media_url.split('/')[-1].split('?')[0]

                # v1.1 twitter api to upload media
                media = api.media_upload(
                    filename=filename,
                    file=file_obj,
                )

                # v2 twitter api to create the tweet
                api = authenticate_twitter_v2_api(access_token, access_token_secret)

                tweet = api.create_tweet(
                    text=content, 
                    media_ids=[media.media_id]
                )
            
                tweet_id = tweet.data['id']

                tweet_url = f"https://twitter.com/{screen_name}/status/{tweet_id}"                               
                
                # Save publishing info within Firestore on the specific clip
                clips_ref = db.collection('clips').document(user_id)
                clips_doc = clips_ref.get()

                if clips_doc.exists:
                    existing_saved_clips = clips_doc.to_dict().get('saved', [])

                    for clip in existing_saved_clips:
                        if clip['url'] == media_url:
                            if 'published' not in clip:
                                clip['published'] = {}

                            if 'twitter' not in clip['published']:
                                clip['published']['twitter'] = []

                            clip['published']['twitter'].append({
                                'tweet_url': tweet_url,
                                'published_at': datetime.datetime.now(),
                            })

                    # Update the clips document with the modified array
                    clips_ref.update({
                        'saved': existing_saved_clips
                    })

                return jsonify({'tweet_url': tweet_url}), 200

            except tweepy.errors.TweepyException as e:
                print(e)
                abort(500, str(e))
        else:
            abort(404) # User not found in Firestore

    except Exception as e:
        print('Publish twitter clip error', e)
        abort(500)