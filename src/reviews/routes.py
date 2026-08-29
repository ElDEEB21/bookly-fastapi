from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import Review, User
from src.auth.dependancies import get_current_user
from src.db.main import get_session
from src.reviews.schemas import ReviewCreateModel
from src.reviews.services import ReviewService

review_router = APIRouter()

review_service = ReviewService()

@review_router.post("/book/{book_uid}", response_model=Review, status_code=status.HTTP_201_CREATED)
async def add_review_to_book(
        book_uid: str,
        review_data: ReviewCreateModel,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
):

    new_review = await review_service.add_review_to_book(
        user_email=current_user.email,
        book_uid=book_uid,
        review_data=review_data,
        session=session
    )

    return new_review