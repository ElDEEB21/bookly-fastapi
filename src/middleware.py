import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.requests import Request

logger = logging.getLogger("uvicorn.access")
logger.disabled = True


def register_middleware(app: FastAPI):
    from src.config import Config

    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)
        processing_time = time.time() - start_time

        message = (f"{request.client.host}:{request.client.port} - {request.method} - {request.url.path} - "
                   f"{response.status_code} completed after {processing_time}s")

        logger.info(message)
        return response

    origins = [o.strip() for o in Config.CORS_ORIGINS.split(",") if o.strip()]
    hosts = [h.strip() for h in Config.TRUSTED_HOSTS.split(",") if h.strip()]
    allow_credentials = not (len(origins) == 1 and origins[0] == "*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=allow_credentials,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=hosts,
    )
