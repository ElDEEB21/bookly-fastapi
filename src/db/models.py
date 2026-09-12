import uuid
from datetime import datetime, date, timezone
from typing import List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column
from sqlmodel import SQLModel, Field, Relationship


def _utcnow():
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"
    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    username: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    email: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    first_name: str
    last_name: str
    role: str = Field(
        sa_column=Column(pg.VARCHAR, nullable=False, server_default="user")
    )
    is_verified: bool = Field(default=False)
    password_hash: str = Field(exclude=True)
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow))
    books: List["Book"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"})
    reviews: List["Review"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"})

    def __repr__(self):
        return f"<User {self.username}>"


class BookTag(SQLModel, table=True):
    book_id: uuid.UUID = Field(default=None, foreign_key="books.uid", primary_key=True, ondelete="CASCADE")
    tag_id: uuid.UUID = Field(default=None, foreign_key="tags.uid", primary_key=True, ondelete="CASCADE")


class Book(SQLModel, table=True):
    __tablename__ = 'books'

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4,
        )
    )
    title: str
    author: str
    publisher: str
    published_date: date
    page_count: int
    language: str
    user_uid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid", ondelete="CASCADE")
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow))
    user: Optional["User"] = Relationship(back_populates="books")
    reviews: List["Review"] = Relationship(back_populates="book", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"})
    tags: List["Tag"] = Relationship(link_model=BookTag, back_populates="books", sa_relationship_kwargs={"lazy": "selectin"})

    def __repr__(self):
        return f'<Book {self.title}>'


class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(sa_column=Column(pg.VARCHAR, nullable=False))
    user_uid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid", ondelete="CASCADE")
    book_uid: Optional[uuid.UUID] = Field(default=None, foreign_key="books.uid", ondelete="CASCADE")
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow))
    update_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow))
    user: Optional[User] = Relationship(back_populates="reviews")
    book: Optional[Book] = Relationship(back_populates="reviews")

    def __repr__(self):
        return f"<Review for book {self.book_uid} by user {self.user_uid}>"


class Tag(SQLModel, table=True):
    __tablename__ = "tags"
    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    name: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=_utcnow))
    books: List["Book"] = Relationship(
        link_model=BookTag,
        back_populates="tags",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"
