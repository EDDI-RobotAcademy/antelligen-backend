from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapter.inbound.api.router import router as api_router
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.database.database import engine, Base

settings: Settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(debug=settings.debug, lifespan=lifespan)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=33333)
