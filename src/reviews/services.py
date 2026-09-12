from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.service import UserService
from src.books.service import BookService
from src.db.models import Review
from src.errors import ReviewAlreadyExists
from src.reviews.schemas import ReviewCreateModel

book_service = BookService()
user_service = UserService()


class ReviewService:

    async def add_review_to_book(
            self,
            user_uid: str,
            book_uid: str,
            review_data: ReviewCreateModel,
            session: AsyncSession
    ):
        book = await book_service.get_book(session, book_uid)
        user = await user_service.get_user_by_uid(session, user_uid)

        existing = await session.exec(
            select(Review).where(Review.book_uid == book.uid, Review.user_uid == user.uid)
        )
        if existing.first() is not None:
            raise ReviewAlreadyExists()

        review_data_dict = review_data.model_dump()
        new_review = Review(
            **review_data_dict
        )

        new_review.user_uid = user.uid
        new_review.book_uid = book.uid

        session.add(new_review)
        await session.commit()
        await session.refresh(new_review)

        return new_review
