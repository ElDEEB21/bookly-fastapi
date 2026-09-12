from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.db.redis import REFRESH_JTI_EXPIRY, ACCESS_JTI_EXPIRY, add_jti_to_blocklist, check_rate_limit
from src.errors import InvalidToken, UserNotFound
from src.celeryTasks import send_email
from .dependencies import (
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
    PasswordResetConfirmModel,
    ResendVerificationModel,
    UserRoleUpdateModel
)
from .service import UserService
from .utils import EMAIL_VERIFICATION_SALT, PASSWORD_RESET_SALT, create_access_token, create_url_safe_token, decode_url_safe_token
from ..config import Config

auth_router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(allowed_roles=["admin", "user"])

REFRESH_TOKEN_EXPIRY = 2


def _build_auth_link(path: str) -> str:
    return f"{Config.SCHEME}://{Config.DOMAIN}{path}"


@auth_router.post('/send_mail', dependencies=[Depends(RoleChecker(allowed_roles=["admin"]))])
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
    token_data = decode_url_safe_token(token, max_age=3600, salt=EMAIL_VERIFICATION_SALT)
    if not token_data:
        return JSONResponse(
            content={"message": "Invalid or expired token"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    email = token_data.get("email")
    uid = token_data.get("uid")

    if not email or not uid:
        return JSONResponse(
            content={"message": "Invalid token or user not found"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

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


@auth_router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
)
async def create_user_Account(
        user_data: UserCreateModel,
        session: AsyncSession = Depends(get_session)
):
    new_user = await user_service.create_user(session, user_data)

    token = create_url_safe_token({"email": new_user.email, "uid": str(new_user.uid)}, salt=EMAIL_VERIFICATION_SALT)

    link = _build_auth_link(f"/api/v1/auth/verify/{token}")

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
        "user": {
            "uid": str(new_user.uid),
            "username": new_user.username,
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "is_verified": new_user.is_verified,
        },
    }


@auth_router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
)
async def resend_verification(email_data: ResendVerificationModel, session: AsyncSession = Depends(get_session)):
    allowed = await check_rate_limit(f"resend:{email_data.email}", limit=3, window_seconds=3600)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    user = await user_service.get_user_by_email(session, email_data.email)
    if not user:
        return JSONResponse(content={"message": "If the email exists, a verification link was sent"}, status_code=status.HTTP_200_OK)
    if user.is_verified:
        return JSONResponse(content={"message": "Email already verified"}, status_code=status.HTTP_200_OK)
    token = create_url_safe_token({"email": user.email, "uid": str(user.uid)}, salt=EMAIL_VERIFICATION_SALT)
    link = _build_auth_link(f"/api/v1/auth/verify/{token}")
    html_message = f"""
    <h1>Verify your email</h1>
    <p>Click the link below to verify your email address:</p>
    <a href="{link}">Verify Email</a>
    """
    send_email.delay(recipients=[user.email], subject="Verify Your Email", body=html_message)
    return JSONResponse(content={"message": "Verification email sent"}, status_code=status.HTTP_200_OK)


@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login_user(login_data: UserLoginModel, session: AsyncSession = Depends(get_session)):
    allowed = await check_rate_limit(f"login:{login_data.email}", limit=5, window_seconds=300)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")
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


@auth_router.post('/refresh_token')
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    new_access_token = create_access_token(
        user_data=token_details['user']
    )

    return JSONResponse(content={'access_token': new_access_token})


@auth_router.get('/me', response_model=UserBooksModel)
async def get_current_user(user=Depends(get_current_user), _: bool = Depends(role_checker)):
    return user


@auth_router.patch('/{user_uid}/role', dependencies=[Depends(RoleChecker(allowed_roles=["admin"]))])
async def update_user_role(user_uid: str, role_data: UserRoleUpdateModel, session: AsyncSession = Depends(get_session)):
    target = await user_service.get_user_by_uid(session, user_uid)
    if not target:
        raise UserNotFound()
    updated = await user_service.update_role(session, target, role_data.role)
    return {"uid": str(updated.uid), "email": updated.email, "role": updated.role}


@auth_router.post('/logout')
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
    jti = token_details.get('jti')
    exp = token_details.get('exp')
    ttl = ACCESS_JTI_EXPIRY
    if exp:
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        if remaining > 0:
            ttl = min(remaining, REFRESH_JTI_EXPIRY)
    await add_jti_to_blocklist(jti, expiry=ttl)

    return JSONResponse(
        content={
            "message": "Successfully logged out",
        },
        status_code=status.HTTP_200_OK
    )


@auth_router.post('/password-reset-confirm/{token}')
async def password_reset_confirm(token: str, password_data: PasswordResetConfirmModel, session: AsyncSession = Depends(get_session)):
    token_data = decode_url_safe_token(token, max_age=3600, salt=PASSWORD_RESET_SALT)
    if not token_data:
        raise InvalidToken()

    email = token_data.get("email")
    uid = token_data.get("uid")

    if not email or not uid:
        raise InvalidToken()

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


@auth_router.post('/password-reset-request')
async def password_reset_request(email_data: PasswordResetRequestModel, session: AsyncSession = Depends(get_session)):
    allowed = await check_rate_limit(f"reset:{email_data.email}", limit=3, window_seconds=3600)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    email = email_data.email

    user = await user_service.get_user_by_email(session, email)

    if not user:
        return JSONResponse(
            content={"message": "If the email exists, a reset link was sent"},
            status_code=status.HTTP_200_OK
        )

    token = create_url_safe_token({"email": user.email, "uid": str(user.uid)}, salt=PASSWORD_RESET_SALT)

    link = _build_auth_link(f"/api/v1/auth/password-reset-confirm/{token}")

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
