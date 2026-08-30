from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.db.redis import add_jti_to_blocklist
from src.errors import InvalidToken
from .dependancies import (
    RefreshTokenBearer,
    AccessTokenBearer,
    get_current_user,
    RoleChecker
)
from .schemas import (
    UserCreateModel,
    UserModel,
    UserLoginModel,
    UserBooksModel
)
from .service import UserService
from .utils import create_access_token

auth_router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(allowed_roles=["admin", "user"])

REFRESH_TOKEN_EXPIRY = 2


@auth_router.post(
    "/signup",
    response_model=UserModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_Account(
        user_data: UserCreateModel,
        session: AsyncSession = Depends(get_session)
):
    new_user = await user_service.create_user(session, user_data)
    return new_user


@auth_router.post(
    "/login",
    response_model=UserLoginModel,
    status_code=status.HTTP_200_OK,
)
async def login_user(login_data: UserLoginModel, session: AsyncSession = Depends(get_session)):
    email = login_data.email
    password = login_data.password

    user = await user_service.authenticate_user(session, email, password)

    access_token = create_access_token(
        user_data={
            'email': user.email,
            'user_uuid': str(user.uid),
            "role": user.role,
        }
    )

    refresh_token = create_access_token(
        user_data={
            'email': user.email,
            'user_uuid': str(user.uid),
        },
        refresh=True,
        expiry=timedelta(days=REFRESH_TOKEN_EXPIRY)
    )

    return JSONResponse(
        content={
            "message": "Successfully logged in",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "email": user.email,
                "uid": str(user.uid),
            }
        }
    )


@auth_router.get('/refresh_token')
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details['exp']

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(
            user_data=token_details['user']
        )

        return JSONResponse(content={'access_token': new_access_token})

    raise InvalidToken()


@auth_router.get('/me', response_model=UserBooksModel)
async def get_current_user(user=Depends(get_current_user), _: bool = Depends(role_checker)):
    return user


@auth_router.get('/logout')
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
    jti = token_details['jti']

    await add_jti_to_blocklist(jti)

    return JSONResponse(
        content={
            "message": "Successfully logged out",
        },
        status_code=status.HTTP_200_OK
    )
