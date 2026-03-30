import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.adapter.inbound.api.v1_router import api_v1_router
from app.domains.stock_theme.adapter.outbound.persistence.stock_theme_repository_impl import StockThemeRepositoryImpl
from app.domains.stock_theme.application.usecase.seed_stock_themes_usecase import SeedStockThemesUseCase
from app.domains.authentication.adapter.inbound.api.authentication_router import router as authentication_router
from app.common.exception.global_exception_handler import register_exception_handlers
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.config.logging_config import setup_logging
from app.infrastructure.config.langsmith_config import configure_langsmith
from app.infrastructure.database.database import AsyncSessionLocal, Base, engine

import app.domains.account.infrastructure.orm.account_orm  # noqa: F401
import app.domains.news.infrastructure.orm.saved_article_orm  # noqa: F401
import app.domains.board.infrastructure.orm.board_orm  # noqa: F401
import app.domains.post.infrastructure.orm.post_orm  # noqa: F401
import app.domains.stock_theme.infrastructure.orm.stock_theme_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.company_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.company_data_coverage_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.disclosure_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.disclosure_document_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.collection_job_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.collection_job_item_orm  # noqa: F401
import app.domains.disclosure.infrastructure.orm.rag_document_chunk_orm  # noqa: F401

setup_logging()
configure_langsmith()

settings: Settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    # Seed stock themes
    async with AsyncSessionLocal() as session:
        await SeedStockThemesUseCase(StockThemeRepositoryImpl(session)).execute()

    # Bootstrap initial data (runs only when companies table is empty)
    from app.infrastructure.scheduler.disclosure_jobs import job_bootstrap

    try:
        await job_bootstrap()
    except Exception as e:
        logging.getLogger(__name__).error("Bootstrap failed (server continues normally): %s", str(e))

    from app.infrastructure.scheduler.disclosure_scheduler import create_disclosure_scheduler

    scheduler = create_disclosure_scheduler()
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allowed_frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)
app.include_router(authentication_router)
register_exception_handlers(app)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=33333)
