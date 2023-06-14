import os
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()

# access environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_MEDIA_BUCKET = os.getenv('AWS_S3_MEDIA_BUCKET')
AWS_S3_TEMP_BUCKET = os.getenv('AWS_S3_TEMP_BUCKET')

TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')

MODE = os.getenv('MODE')
