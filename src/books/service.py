from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc

from src.db.models import Book
from .schemas import BookCreateModel, BookUpdateModel


class BookService:
    async def get_all_books(self, session: AsyncSession):
        statement = select(Book).order_by(desc(Book.created_at))
        result = await session.exec(statement)
        return result.all()

    async def get_user_books(self, user_uid: str, session: AsyncSession):
        statement = select(Book).where(Book.user_uid == user_uid).order_by(desc(Book.created_at))
        result = await session.exec(statement)
        return result.all()

    async def get_book(self, session: AsyncSession, book_uuid: str):
        statement = select(Book).where(Book.uid == book_uuid)
        result = await session.exec(statement)
        book = result.first()

        return book if book else None

    async def create_book(self, session: AsyncSession, book_data: BookCreateModel, user_id: str):
        new_book = Book(**book_data.model_dump())

        new_book.published_date = datetime.strptime(book_data.published_date, "%Y-%m-%d").date()

        new_book.user_uid = user_id

        session.add(new_book)
        await session.commit()
        await session.refresh(new_book)

        return new_book

    async def update_book(self, session: AsyncSession, book_uuid: str, book_data: BookUpdateModel):
        book = await self.get_book(session, book_uuid)
        if not book:
            return None

        for key, value in book_data.model_dump().items():
            setattr(book, key, value)
        await session.commit()
        await session.refresh(book)

        return book

    async def delete_book(self, session: AsyncSession, book_uuid: str):
        book = await self.get_book(session, book_uuid)
        if not book:
            return None

        await session.delete(book)
        await session.commit()

        return book
