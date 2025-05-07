from fastapi import APIRouter, Depends
# from app.services.user_service import UserService
from app.schemas.auth import UserInfo
from app.utils.jwt_handler import get_current_user

router = APIRouter()


@router.get("/current-user", response_model=UserInfo)
async def read_current_user(current_user: UserInfo = Depends(get_current_user)):
    return current_user

@router.post("/" )
async def post_user():
    return 'ok'

