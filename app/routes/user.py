from fastapi import APIRouter, Depends
# from app.services.user_service import UserService
from app.schemas.auth import UserInfo
from app.utils.jwt_handler import get_current_user

router = APIRouter()


@router.get("/current-user", response_model=UserInfo)
async def read_current_user(current_user: UserInfo = Depends(get_current_user)):
    return current_user

@router.post("/", response_model=UserInfo)
async def user_porfile( ):
    """
    we are register the user here and compelet the all profile data 
    """
    return 'ok'
@router.get('/', response_model=UserInfo)

async def get_user_profile():
    """
    get the user profile and user all data for api and get all user profile data

    """
    return 'ok'

