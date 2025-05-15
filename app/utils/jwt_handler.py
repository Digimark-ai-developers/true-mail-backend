from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import UserInfo
from app.utils.firebase import verify_firebase_token

SECRET_KEY = "VqgYZ=mhQa8VTq75-)t6V|m3;o!4@nG$+KsX[;*;$$?[S_c=?!'qTU5*hMC*p*|C"
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 60
bearer_scheme = HTTPBearer()


def create_jwt_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserInfo:
    try:
        id_token = credentials.credentials
        decoded_token = verify_firebase_token(id_token)  # Verifies with Firebase

        return UserInfo(
            user_Id=decoded_token.get("uid"),
            email=decoded_token.get("email"),
            first_name=decoded_token.get("name", ""),
            last_name="",  # Firebase doesn't provide separate last name
            photoURL=decoded_token.get("picture", ""),
        )

    except Exception as err:
        print("Firebase token verification failed:", err)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Firebase token",
        headers={"WWW-Authenticate": "Bearer"},
    )
