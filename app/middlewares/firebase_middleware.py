# app/middlewares/firebase_middleware.py
from fastapi import Request, HTTPException
from firebase_admin import auth, credentials, initialize_app
import firebase_admin

if not firebase_admin._apps:
    cred = credentials.Certificate("app/firebase-adminsdk.json")
    initialize_app(cred)

async def verify_firebase_token(request: Request):
    token = request.headers.get("Authorization")
    
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    try:
        decoded_token = auth.verify_id_token(token.replace("Bearer ", ""))
        request.state.firebase_user = decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    
 
 
 