from fastapi import FastAPI, status
from src.books.routes import book_router
from contextlib import asynccontextmanager
from src.db.main import init_db


@asynccontextmanager
async def life_span(app: FastAPI):
    print(f"Server is Starting ...")
    await init_db()
    yield
    print("Server has been stopped")

version = "v1"

app = FastAPI(
    title="Bookly",
    description="A REST API for Books",
    version=version,
    lifespan=life_span,
)

app.include_router(book_router, prefix=f"/api/{version}/books", tags=["books"])



