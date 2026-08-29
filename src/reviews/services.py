from fastapi import status
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.service import UserService
from src.books.service import BookService
from src.db.models import Review
from src.reviews.schemas import ReviewCreateModel

book_service = BookService()
user_service = UserService()


class ReviewService:

    async def add_review_to_book(
            self,
            user_email: str,
            book_uid: str,
            review_data: ReviewCreateModel,
            session: AsyncSession
    ):
        try:
            book = await book_service.get_book(session, book_uid)
            user = await user_service.get_user_by_email(session, user_email)

            review_data_dict = review_data.model_dump()
            new_review = Review(
                **review_data_dict
            )

            new_review.user = user
            new_review.book = book

            if not book:
                raise HTTPException(
                    detail="Book not found", status_code=status.HTTP_404_NOT_FOUND
                )

            if not user:
                raise HTTPException(
                    detail="User not found", status_code=status.HTTP_404_NOT_FOUND
                )

            session.add(new_review)
            await session.commit()
            await session.refresh(new_review)

            return new_review

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Oops, something went wrong",
            )
