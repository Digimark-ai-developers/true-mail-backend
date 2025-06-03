# app/services/user_service.py
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.credits import Credit
from app.models.user import User
from app.schemas.user import UserProfileRead, UserProfileUpdate


def fetch_user_profile(user_id: str, db: Session) -> UserProfileRead:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    credit = db.query(Credit).filter(Credit.user_id == user_id).first()

    user_data = UserProfileRead.model_validate(user)

    # Add credit info if available
    if credit:
        user_data.total_credits = credit.total_credits
        user_data.remaining_credits = credit.remaining_credits

    return user_data


def update_user_profile(user_id, user_data: UserProfileUpdate, db: Session) -> UserProfileUpdate:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    update_fields = user_data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return UserProfileUpdate.model_validate(user)
