from flask import abort, jsonify
import tweepy
from config import TWITTER_API_KEY, TWITTER_API_SECRET
from firestore_client import db

def clips_publish_twitter():
    return 'SUccess', 200