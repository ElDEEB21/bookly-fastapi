from .models import User
from .schemas import UserCreateModel
from .utils import generate_passwd_hash, verify_password
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

class UserService:
    async def get_user_by_email(self, session: AsyncSession, email: str):
        statement = select(User).where(User.email == email)

        result = await session.exec(statement)
        user = result.first()

        return user

    async def get_user_by_username(self, session: AsyncSession, username: str):
        statement = select(User).where(User.username == username)

        result = await session.exec(statement)
        user = result.first()

        return user

    async def user_email_exists(self, session: AsyncSession, email: str):
        user_email = await self.get_user_by_email(session, email)
        return user_email is not None

    async def user_username_exists(self, session: AsyncSession, username: str):
        user_username = await self.get_user_by_username(session, username)
        return user_username is not None

    async def create_user(self, session: AsyncSession, user_data: UserCreateModel):
        user_data_dict = user_data.model_dump()

        new_user = User(**user_data_dict)
        new_user.password_hash = generate_passwd_hash(user_data_dict["password"])
        new_user.role = "user"

        session.add(new_user)
        await session.commit()

        return new_user