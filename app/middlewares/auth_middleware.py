from fastapi import Request, HTTPException
from app.utils.firebase_utils import verify_id_token

async def firebase_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/auth"):
        return await call_next(request)

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")

    try:
        id_token = authorization.split("Bearer ")[1]
        decoded_token = verify_id_token(id_token)
        request.state.user = decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Token")

    return await call_next(request)