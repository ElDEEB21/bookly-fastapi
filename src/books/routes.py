from typing import List

from fastapi import APIRouter, status, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import AccessTokenBearer, RoleChecker, get_current_user
from src.db.main import get_session
from src.db.models import User
from src.errors import NotBookOwner
from .schemas import Book, BookUpdateModel, BookCreateModel, BookDetailModel
from .service import BookService

book_router = APIRouter()
book_service = BookService()
access_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user"]))


def _ensure_book_owner(book, current_user: User):
    if current_user.role == "admin":
        return
    if book.user_uid is None or str(book.user_uid) != str(current_user.uid):
        raise NotBookOwner()


@book_router.get("", response_model=List[Book], dependencies=[role_checker])
async def get_all_books(
        session: AsyncSession = Depends(get_session),
        token_details: dict = Depends(access_token_bearer),
):
    books = await book_service.get_all_books(session)
    return books


@book_router.get("/user", response_model=List[Book], dependencies=[role_checker])
async def get_user_books(
        session: AsyncSession = Depends(get_session),
        token_details: dict = Depends(access_token_bearer),
):
    user_id = (token_details.get('user') or {}).get('user_uuid')
    books = await book_service.get_user_books(user_id, session)
    return books


@book_router.post("", status_code=status.HTTP_201_CREATED, dependencies=[role_checker])
async def create_a_book(book_data: BookCreateModel, session: AsyncSession = Depends(get_session),
                        token_details: dict = Depends(access_token_bearer)) -> dict:
    user_id = (token_details.get('user') or {}).get('user_uuid')
    new_book = await book_service.create_book(session, book_data, user_id)
    return {"message": "Book created successfully", "book": new_book}


@book_router.get("/{book_uid}", response_model=BookDetailModel, dependencies=[role_checker])
async def get_book(book_uid: str, session: AsyncSession = Depends(get_session),
                   token_details: dict = Depends(access_token_bearer)):
    book = await book_service.get_book(session, book_uid)
    return book


@book_router.patch("/{book_uid}", response_model=Book, dependencies=[role_checker])
async def patch_book(book_uid: str, new_data: BookUpdateModel, session: AsyncSession = Depends(get_session),
                     token_details: dict = Depends(access_token_bearer),
                     current_user: User = Depends(get_current_user)) -> Book:
    book = await book_service.get_book(session, book_uid)
    _ensure_book_owner(book, current_user)
    updated_book = await book_service.update_book(session, book_uid, new_data)
    return updated_book


@book_router.delete("/{book_uid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[role_checker])
async def delete_book(book_uid: str, session: AsyncSession = Depends(get_session),
                      token_details: dict = Depends(access_token_bearer),
                      current_user: User = Depends(get_current_user)):
    book = await book_service.get_book(session, book_uid)
    _ensure_book_owner(book, current_user)
    await book_service.delete_book(session, book_uid)
    return None
