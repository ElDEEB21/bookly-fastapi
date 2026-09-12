from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.db.redis import add_jti_to_blocklist
from src.errors import InvalidToken, UserNotFound
from src.celeryTasks import send_email
from .dependancies import (
    RefreshTokenBearer,
    AccessTokenBearer,
    get_current_user,
    RoleChecker
)
from .schemas import (
    UserCreateModel,
    UserLoginModel,
    UserBooksModel,
    EmailModel,
    PasswordResetRequestModel,
    PasswordResetConfirmModel
)
from .service import UserService
from .utils import create_access_token, create_url_safe_token, decode_url_safe_token
from ..config import Config
from ..mail import create_message, mail

auth_router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(allowed_roles=["admin", "user"])

REFRESH_TOKEN_EXPIRY = 2


@auth_router.post('/send_mail')
async def send_mail(emails: EmailModel):
    emails = emails.addresses

    html = "<h1>Welcome to our app</h1><p>We're excited to have you on board!</p>"

    send_email.delay(recipients=emails, subject="Welcome to our app", body=html)
    return JSONResponse(
        content={"message": "Email sent successfully",},
        status_code=status.HTTP_200_OK
    )


@auth_router.get('/verify/{token}')
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    try:
        token_data = decode_url_safe_token(token, max_age=3600)
        email = token_data.get("email")
        uid = token_data.get("uid")

        user = await user_service.get_user_by_email(session, email)

        if not user or str(user.uid) != uid:
            return JSONResponse(
                content={"message": "Invalid token or user not found"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if user.is_verified:
            return JSONResponse(
                content={"message": "Email already verified"},
                status_code=status.HTTP_200_OK
            )

        await user_service.verify_user(session, user)

        return JSONResponse(
            content={"message": "Email verified successfully"},
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        return JSONResponse(
            content={"message": "Invalid or expired token"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@auth_router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
)
async def create_user_Account(
        user_data: UserCreateModel,
        bg_tasks: BackgroundTasks,
        session: AsyncSession = Depends(get_session)
):
    new_user = await user_service.create_user(session, user_data)

    token = create_url_safe_token({"email": new_user.email, "uid": str(new_user.uid)})

    link = f"http://{Config.DOMAIN}/api/v1/auth/verify/{token}"

    html_message = f"""
    <h1>Welcome to our app</h1>
    <p>We're excited to have you on board! Please verify your email address by clicking
    the link below:</p>
    <a href="{link}">Verify Email</a>
    """

    send_email.delay(
        recipients=[new_user.email],
        subject="Verify Your Email",
        body=html_message
    )

    return {
        "message": "User created successfully. Please check your email to verify your account.",
        "user": new_user,
    }


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


@auth_router.post('/password-reset-confirm/{token}')
async def password_reset_confirm(token: str, password_data: PasswordResetConfirmModel, session: AsyncSession = Depends(get_session)):
    try:
        token_data = decode_url_safe_token(token, max_age=3600)
        email = token_data.get("email")
        uid = token_data.get("uid")

        user = await user_service.get_user_by_email(session, email)

        if not user or str(user.uid) != uid:
            raise UserNotFound()

        if password_data.new_password != password_data.confirm_new_password:
            raise HTTPException(
                detail="Passwords do not match",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await user_service.update_password(session, user, password_data.new_password)

        return JSONResponse(
            content={"message": "Password reset successfully"},
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        return JSONResponse(
            content={"message": "Error occurred during password reset"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@auth_router.post('/password-reset-request')
async def password_reset_request(email_data: PasswordResetRequestModel, session: AsyncSession = Depends(get_session)):
    email = email_data.email

    user = await user_service.get_user_by_email(session, email)

    if not user:
        return JSONResponse(
            content={"message": "User not found"},
            status_code=status.HTTP_404_NOT_FOUND
        )

    token = create_url_safe_token({"email": user.email, "uid": str(user.uid)})

    link = f"http://{Config.DOMAIN}/api/v1/auth/password-reset-confirm/{token}"

    html_message = f"""
    <h1>Password Reset Request</h1>
    <p>We received a request to reset your password. Click the link below to reset your password:</p>
    <a href="{link}">Reset Password</a>
    """

    send_email.delay(
        recipients=[user.email],
        subject="Password Reset Request",
        body=html_message
    )

    return JSONResponse(
        content={"message": "Please check your email for the password reset link."},
        status_code=status.HTTP_200_OK
    )
