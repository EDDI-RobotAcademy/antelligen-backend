from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapter.inbound.api.v1_router import api_v1_router
from app.common.exception.global_exception_handler import register_exception_handlers
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.database.database import engine, Base

# ORM 모델 import — Base.metadata.create_all 시 테이블 자동 생성
import app.domains.post.infrastructure.orm.post_orm  # noqa: F401
import app.domains.news.infrastructure.orm.saved_article_orm  # noqa: F401
import app.domains.account.infrastructure.orm.account_orm  # noqa: F401

settings: Settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(debug=settings.debug, lifespan=lifespan)

app.include_router(api_v1_router)
register_exception_handlers(app)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=33333)
