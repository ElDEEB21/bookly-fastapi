from typing import List

from fastapi import APIRouter, status, Depends
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependancies import AccessTokenBearer, RoleChecker
from src.db.main import get_session
from src.errors import BookNotFound
from .schemas import Book, BookUpdateModel, BookCreateModel, BookDetailModel
from .service import BookService

book_router = APIRouter()
book_service = BookService()
access_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user"]))


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
    user_id = token_details.get('user')['user_uuid']
    books = await book_service.get_user_books(user_id, session)
    return books


@book_router.post("", status_code=status.HTTP_201_CREATED, dependencies=[role_checker])
async def create_a_book(book_data: BookCreateModel, session: AsyncSession = Depends(get_session),
                        token_details: dict = Depends(access_token_bearer)) -> dict:
    user_id = token_details.get('user')['user_uuid']
    new_book = await book_service.create_book(session, book_data, user_id)
    return {"message": "Book created successfully", "book": new_book}


@book_router.get("/{book_uid}", response_model=BookDetailModel, dependencies=[role_checker])
async def get_book(book_uid: str, session: AsyncSession = Depends(get_session),
                   token_details: dict = Depends(access_token_bearer)):
    book = await book_service.get_book(session, book_uid)
    if not book:
        raise BookNotFound()
    return book


@book_router.patch("/{book_uid}", response_model=BookUpdateModel, dependencies=[role_checker])
async def patch_book(book_uid: str, new_data: BookUpdateModel, session: AsyncSession = Depends(get_session),
                     token_details: dict = Depends(access_token_bearer)) -> Book:
    updated_book = await book_service.update_book(session, book_uid, new_data)
    if not updated_book:
        raise BookNotFound()
    return updated_book


@book_router.delete("/{book_uid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[role_checker])
async def delete_book(book_uid: str, session: AsyncSession = Depends(get_session),
                      token_details: dict = Depends(access_token_bearer)):
    deleted_book = await book_service.delete_book(session, book_uid)
    if not deleted_book:
        raise BookNotFound()
    return {}
