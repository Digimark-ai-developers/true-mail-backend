# from fastapi import Request, HTTPException
# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.responses import JSONResponse
# from app.utils.jwt import verify_access_token

# class AuthMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         try:
#             # Skip authentication for public routes and OPTIONS requests
#             public_routes = [
#                 '/', "/auth/login", "/auth/signup", "/auth/google",
#                 "/auth/google/callback", "/docs", "/openapi.json",
#                 '/auth/forgot-password', '/auth/reset-password',
#                 '/otp/verify', '/otp/generate', '/users'
#             ]
#             if request.url.path in public_routes or request.method == "OPTIONS":
#                 return await call_next(request)

#             # Extract Authorization header
#             auth_header = request.headers.get("Authorization")
#             if not auth_header or not auth_header.startswith("Bearer "):
#                 raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid Authorization header")

#             token = auth_header.split(" ")[1]

#             # Verify token
#             user = verify_access_token(token)
#             request.state.user = user  # Attach user info to request state

#             return await call_next(request)

#         except HTTPException as http_exc:
#             # Explicitly handle HTTP exceptions
#             return JSONResponse(
#                 status_code=http_exc.status_code,
#                 content={"detail": http_exc.detail},
#             )
#         except Exception as e:
#             # Handle unexpected exceptions gracefully
#             return JSONResponse(
#                 status_code=500,
#                 content={"detail": "Internal Server Error. Please contact support."},
#             )
