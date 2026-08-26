import logging
import uuid
from datetime import timedelta, datetime

import bcrypt
import jwt

from src.config import Config

ACCESS_TOKEN_EXPIRY = 3600


def generate_passwd_hash(password: str):
    password = password.encode('utf-8')
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")
    return hashed_password


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(user_data: dict, expiry: timedelta = None, refresh: bool = False):
    payload = {
        'user': user_data,
        'exp': datetime.now() + (expiry if expiry else timedelta(seconds=ACCESS_TOKEN_EXPIRY)),
        'jti': str(uuid.uuid4()),
        'refresh': refresh,
    }

    token = jwt.encode(
        payload=payload,
        key=Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM
    )
    return token


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return token_data

    except jwt.PyJWTError as e:
        logging.exception(e)
        return None
