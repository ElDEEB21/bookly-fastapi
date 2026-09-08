import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from src.books.schemas import Book
from src.db.models import Review


class UserCreateModel(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    username: str = Field(max_length=8)
    email: str = Field(max_length=128)
    password: str = Field(min_length=8)


class UserModel(BaseModel):
    uid: uuid.UUID
    username: str
    email: str
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
    email: str = Field(max_length=128)
    password: str = Field(min_length=8)


class EmailModel(BaseModel):
    addresses: List[str]

class PasswordResetRequestModel(BaseModel):
    email: str = Field(max_length=128)

class PasswordResetConfirmModel(BaseModel):
    new_password: str = Field(min_length=8)
    confirm_new_password: str = Field(min_length=8)