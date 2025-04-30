import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Path to Firebase credentials
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")

# Initialize Firebase Admin SDK
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)

# Verify Firebase ID Token
def verify_id_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError("Invalid Firebase ID Token") from e