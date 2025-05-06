# from fastapi import Depends, HTTPException, Request, status
# from app.utils.firebase import verify_firebase_token

# def get_current_user(request: Request):
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")

#     token = auth_header.split(" ")[1]
#     try:
#         decoded_user = verify_firebase_token(token)
#         return decoded_user  # you can use uid/email/etc. from this
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
