import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Depends, Request
from functools import wraps

# Initialize Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate("app/firebase-adminsdk.json")
    firebase_admin.initialize_app(cred)

def verify_firebase_token(request: Request):
    """Extract and verify Firebase token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = auth_header.split("Bearer ")[-1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # Contains uid, email, etc.
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
