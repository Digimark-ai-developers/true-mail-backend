from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.models.user import User

# from app.services.user_service import UserService
from app.schemas.auth import UserInfo
from app.schemas.user import UserProfileRead, UserProfileUpdate
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/user", tags=["User "])


@router.get("/{user_id}")
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_dict = jsonable_encoder(user)
    return JSONResponse(
        status_code=status.HTTP_302_FOUND, content={"message": "User found successfully.", "data": user_dict}
    )


@router.put("/{user_id}/update")
def update_user_profile(user_id: str, user_data: UserProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_fields = user_data.dict(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    user_dict = jsonable_encoder(user)
    return JSONResponse(
        status_code=status.HTTP_302_FOUND, content={"message": "User updated successfully.", "data": user_dict}
    )


# @router.delete("/{user_id}")
# def delete_user(user_id: str, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.user_id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
#         )

#     user.deleted_at = datetime.utcnow()
#     user.status = False
#     db.commit()
#     return {"detail": "User marked as deleted"}


@router.get("/")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.status == True).all()
    user_dict = jsonable_encoder(users)
    return JSONResponse(
        status_code=status.HTTP_302_FOUND, content={"message": "User data read successfully.", "data": user_dict}
    )
