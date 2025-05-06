import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase App
cred_path = "./app/truemail-5a597-firebase-adminsdk-fbsvc-529130fcbb.json"
cred = credentials.Certificate(cred_path)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str):
    """Verify Firebase ID token and return the decoded user info."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token  # contains uid, email, etc.
    except Exception as e:
        raise ValueError(f"Invalid Firebase token: {str(e)}")
