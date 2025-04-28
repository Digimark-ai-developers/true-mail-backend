from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone_number: Optional[str] = None


class UserResponse(BaseModel):
    id: str  # The encrypted ID sent to the client as a string
    username: str
    email: str
    phone_number: Optional[str]
    profile_picture_url: Optional[str]
    is_verified: bool

    # Automatically encrypt user_id before sending the response
    @model_validator(mode="before")
    def encrypt_user_id(cls, values):
        if "id" in values:
            print('VALUES',values)

            # Encrypt the integer ID and convert to string
            values["id"] = encrypt_data(values["id"])  # Assumed encryption returns a string
            print('XXXXX',type(values["id"]))

        return values

    # Decrypt user_id when receiving data from frontend
    @model_validator(mode="after")
    def decrypt_user_id(cls, values):
        if "id" in values:
            # Decrypt the ID (it's a string here, converting back to integer as needed)
            values["id"] = decrypt_data(values["id"])  # Assumed decryption returns an integer
        return values