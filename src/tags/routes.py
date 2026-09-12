from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession


from src.auth.dependencies import RoleChecker, get_current_user
from src.books.service import BookService
from src.db.main import get_session
from src.db.models import User
from src.errors import NotBookOwner

from .schemas import TagAddModel, TagCreateModel, TagModel
from .service import TagService

tags_router = APIRouter()
tag_service = TagService()
book_service = BookService()
user_role_checker = Depends(RoleChecker(["user", "admin"]))
admin_role_checker = Depends(RoleChecker(["admin"]))


@tags_router.get("/", response_model=List[TagModel], dependencies=[user_role_checker])
async def get_all_tags(session: AsyncSession = Depends(get_session)):
    tags = await tag_service.get_tags(session)

    return tags


@tags_router.post(
    "/",
    response_model=TagModel,
    status_code=status.HTTP_201_CREATED,
    dependencies=[admin_role_checker],
)
async def add_tag(
    tag_data: TagCreateModel, session: AsyncSession = Depends(get_session)
) -> TagModel:

    tag_added = await tag_service.add_tag(tag_data=tag_data, session=session)

    return tag_added


@tags_router.post(
    "/book/{book_uid}/tags", response_model=List[TagModel], dependencies=[user_role_checker]
)
async def add_tags_to_book(
    book_uid: str, tag_data: TagAddModel, session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> List[TagModel]:
    book = await book_service.get_book(session, book_uid)
    if current_user.role != "admin" and (book.user_uid is None or str(book.user_uid) != str(current_user.uid)):
        raise NotBookOwner()

    tags = await tag_service.add_tags_to_book(
        book_uid=book_uid, tag_data=tag_data, session=session
    )

    return tags


@tags_router.put(
    "/{tag_uid}", response_model=TagModel, dependencies=[admin_role_checker]
)
async def update_tag(
    tag_uid: str,
    tag_update_data: TagCreateModel,
    session: AsyncSession = Depends(get_session),
) -> TagModel:
    updated_tag = await tag_service.update_tag(tag_uid, tag_update_data, session)

    return updated_tag


@tags_router.delete(
    "/{tag_uid}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[admin_role_checker],
)
async def delete_tag(
    tag_uid: str, session: AsyncSession = Depends(get_session)
) -> None:
    await tag_service.delete_tag(tag_uid, session)

    return None