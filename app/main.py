import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import webhook, calls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (use Alembic migrations for production)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI Receptionist — Backend API",
    description="Receives Vapi.ai webhooks and exposes call report data for the dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this to your dashboard domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(calls.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
