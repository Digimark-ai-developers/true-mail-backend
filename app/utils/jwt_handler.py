import jwt
from datetime import datetime, timedelta

SECRET_KEY = "VqgYZ=mhQa8VTq75-)t6V|m3;o!4@nG$+KsX[;*;$$?[S_c=?!'qTU5*hMC*p*|C"
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 60

def create_jwt_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
