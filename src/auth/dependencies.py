from typing import List

from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import User
from src.db.redis import token_in_blocklist
from src.errors import (
    InvalidToken,
    RevokedToken,
    RefreshTokenRequired,
    AccessTokenRequired,
    InsufficientPermission,
    UserNotFound, AccountNotVerified,
)
from .service import UserService
from .utils import decode_token
from ..db.main import get_session

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        creds = await super().__call__(request)

        if creds is None:
            raise InvalidToken()

        token = creds.credentials
        token_data = decode_token(token)

        if not self.token_valid(token_data):
            raise InvalidToken()
        if await token_in_blocklist(token_data.get('jti', '')):
            raise RevokedToken()

        self.verify_token_data(token_data)

        return token_data

    def token_valid(self, token_data: dict | None) -> bool:
        return token_data is not None and isinstance(token_data, dict)

    def verify_token_data(self, token_data: dict):
        raise NotImplementedError("Please implement this method in child class")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data.get('refresh', False):
            raise AccessTokenRequired()


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data.get('refresh', False):
            raise RefreshTokenRequired()


async def get_current_user(token_details: dict = Depends(AccessTokenBearer()),
                           session: AsyncSession = Depends(get_session)):
    user_info = token_details.get('user', {}) if isinstance(token_details, dict) else {}
    user = None
    if user_info.get('user_uuid'):
        statement_user = user_info.get('user_uuid')
        from sqlmodel import select
        statement = select(User).where(User.uid == statement_user)
        result = await session.exec(statement)
        user = result.first()
    if user is None and user_info.get('email'):
        user = await user_service.get_user_by_email(session, user_info.get('email'))
    if not user:
        raise UserNotFound()
    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if not current_user.is_verified:
            raise AccountNotVerified()

        if current_user.role in self.allowed_roles:
            return True
        raise InsufficientPermission()
