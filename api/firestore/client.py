import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from api.constants import FIREBASE_SERVICE_ACCOUNT_KEY
import json


# Initialize Firebase Admin SDK with the service account key
# Replace with the path to your service account key JSON file
cred = credentials.Certificate(json.loads(FIREBASE_SERVICE_ACCOUNT_KEY))
firebase_admin.initialize_app(cred)

# Initialize Firestore client
db = firestore.client()
