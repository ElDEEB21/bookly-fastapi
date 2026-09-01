from fastapi import FastAPI

from .auth.routes import auth_router
from .books.routes import book_router
from .errors import register_all_errors
from .middleware import register_middleware
from .reviews.routes import review_router
from .tags.routes import tags_router

version = "v1"

app = FastAPI(
    title="Bookly",
    description="A REST API for Books",
    version=version,
)

register_all_errors(app)
register_middleware(app)

app.include_router(book_router, prefix=f"/api/{version}/books", tags=["books"])
app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["auth"])
app.include_router(review_router, prefix=f"/api/{version}/reviews", tags=["reviews"])
app.include_router(tags_router, prefix=f"/api/{version}/tags", tags=["tags"])
