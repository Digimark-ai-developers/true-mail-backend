from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from firebase_admin import auth
import firebase_admin

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/auth"):  # Skip auth routes
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
        id_token = auth_header.split(" ")[1]

        try:
            decoded_token = auth.verify_id_token(id_token)
            request.state.user = decoded_token
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")

        return await call_next(request)
    
