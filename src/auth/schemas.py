import re
import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.books.schemas import Book
from src.db.models import Review


def _validate_password_strength(value: str) -> str:
    if len(value) < 8 or len(value) > 128:
        raise ValueError("Password must be between 8 and 128 characters")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password must contain a digit")
    return value


class UserCreateModel(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr = Field(max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserModel(BaseModel):
    uid: uuid.UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    is_verified: bool
    password_hash: str = Field(exclude=True)
    created_at: datetime
    updated_at: datetime

class UserBooksModel(UserModel):
    books: List[Book]
    reviews: List[Review]


class UserLoginModel(BaseModel):
    email: EmailStr = Field(max_length=128)
    password: str = Field(min_length=8, max_length=128)


class EmailModel(BaseModel):
    addresses: List[EmailStr]

class PasswordResetRequestModel(BaseModel):
    email: EmailStr = Field(max_length=128)

class PasswordResetConfirmModel(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)

class ResendVerificationModel(BaseModel):
    email: EmailStr = Field(max_length=128)

class UserRoleUpdateModel(BaseModel):
    role: str = Field(pattern="^(admin|user)$")