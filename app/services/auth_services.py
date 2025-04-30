
from app.database.db_config import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.database.db_config import SessionLocal

async def sync_firebase_user(firebase_user_data: dict) -> UserResponse:
    from app.database.db_config import async_session  # get async DB session

    async with async_session() as session:
        stmt = select(User).where(User.email == firebase_user_data["email"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return UserResponse.model_validate(user)

        # Create new user
        new_user = User(
            email=firebase_user_data["email"],
            first_name=firebase_user_data.get("name", ""),
            last_name="",  # Firebase doesn't have this by default
            address="",
            city="",
            isEmailVerified=firebase_user_data.get("email_verified", False),
            gender="",
            photoURL=firebase_user_data.get("picture", ""),
            creditBalance=10,  # Starting free credit
            stripeCustomerId="",
            emailsTest="",
            cuntry="",
            state="",
            zip_cod=0,
            createdAt=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=datetime.utcnow(),
            deleted_by=datetime.utcnow(),
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return UserResponse.model_validate(new_user)



def create_user_in_db(uid: str, email: str, name: str):
    db = SessionLocal()
    try:
        user = User(uid=uid, email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    finally:
        db.close()