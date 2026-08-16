from fastapi import APIRouter, status, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import Book, BookUpdateModel, BookCreateModel
from .service import BookService
from src.db.main import get_session
from typing import List

book_router = APIRouter()
book_service = BookService()


@book_router.get("",response_model=List[Book])
async def get_all_books(session: AsyncSession = Depends(get_session)):
    books = await book_service.get_all_books(session)
    return books

@book_router.post("", status_code=status.HTTP_201_CREATED)
async def create_a_book(book_data: BookCreateModel, session: AsyncSession = Depends(get_session)) -> dict:
    new_book = await book_service.create_book(session, book_data)
    return {"message": "Book created successfully", "book": new_book}


@book_router.get("/{book_uid}", response_model=Book)
async def get_book(book_uid: str, session: AsyncSession = Depends(get_session)):
    book = await book_service.get_book(session, book_uid)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@book_router.patch("/{book_uid}", response_model=BookUpdateModel)
async def patch_book(book_uid: str, new_data: BookUpdateModel, session: AsyncSession = Depends(get_session)) -> Book:
    updated_book = await book_service.update_book(session, book_uid, new_data)
    if not updated_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated_book

@book_router.delete("/{book_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_uid: str, session: AsyncSession = Depends(get_session)):
    deleted_book = await book_service.delete_book(session, book_uid)
    if not deleted_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return None
