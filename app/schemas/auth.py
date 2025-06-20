from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

class LoginResponse(BaseModel):
    message: str
    status: int
    data: TokenResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

class OTPRequest(BaseModel):
    otp: int

class GenericSuccess(BaseModel):
    message: str
    status: int
    data: Dict[str, Any]
