from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.mongodb import close_mongo_client
from app.core.redis_client import close_redis_client
from app.core.storage import get_storage_service

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await get_storage_service().ensure_bucket_exists()
    yield
    await close_mongo_client()
    await close_redis_client()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
