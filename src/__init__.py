from fastapi import FastAPI, status
from src.books.routes import book_router
from src.auth.routes import auth_router
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
)

app.include_router(book_router, prefix=f"/api/{version}/books", tags=["books"])
app.include_router(auth_router, prefix=f"/api/{version}/auth" ,tags=["auth"])



