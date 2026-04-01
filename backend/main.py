import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, AsyncSessionLocal
from app.routers import dashboard, ebay, statements, research, prospects, tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _daily_prospect_refresh():
    logger.info("Running scheduled prospect refresh...")
    async with AsyncSessionLocal() as db:
        from app.services.mlb_prospects import fetch_and_store_prospects
        count = await fetch_and_store_prospects(db)
        logger.info(f"Prospect refresh complete: {count} updated")


async def _weekly_price_snapshot():
    logger.info("Running scheduled weekly price snapshot...")
    async with AsyncSessionLocal() as db:
        from app.services.price_tracker import snapshot_all_watchlist
        stats = await snapshot_all_watchlist(db)
        logger.info(f"Price snapshot complete: {stats}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized")

    # Schedule jobs
    scheduler.add_job(_daily_prospect_refresh, "cron", hour=6, minute=0, id="prospect_refresh")
    scheduler.add_job(_weekly_price_snapshot, "cron", day_of_week="sun", hour=7, minute=0, id="price_snapshot")
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Sports Card Business Dashboard",
    description="Track P&L, research cards, monitor MLB prospects, and track card prices.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(ebay.router, prefix=API_PREFIX)
app.include_router(statements.router, prefix=API_PREFIX)
app.include_router(research.router, prefix=API_PREFIX)
app.include_router(prospects.router, prefix=API_PREFIX)
app.include_router(tracker.router, prefix=API_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
