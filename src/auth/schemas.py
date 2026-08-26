from pydantic import BaseModel, Field
import uuid
from datetime import datetime

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

class UserLoginModel(BaseModel):
    email: str = Field(max_length=128)
    password: str = Field(min_length=8)