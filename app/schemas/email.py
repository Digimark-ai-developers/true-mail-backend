from pydantic import BaseModel, EmailStr

class CheckEmailRequest(BaseModel):
    email: EmailStr