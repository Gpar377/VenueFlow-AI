"""
VenueFlow AI — FastAPI Application
Refactored for enterprise standards: structured logging, lifespan management, and global error handling.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import logger, log_event
from app.security import SecurityMiddleware
from app.simulation.venue import Venue
from app.simulation.crowd_engine import CrowdEngine
from app.simulation.queue_engine import QueueEngine
from app.simulation.event_timeline import EventTimeline
from app.api.routes import router as api_router, set_simulation_state
from app.api.websocket import websocket_endpoint, simulation_broadcast_loop


# ── Simulation State ──────────────────────────────────────────

sim_state = {}

def init_simulation():
    """Initialize the venue simulation with standard configuration."""
    logger.info("Initializing simulation engines...")
    venue = Venue(capacity=settings.VENUE_CAPACITY)
    timeline = EventTimeline()
    crowd_engine = CrowdEngine(venue, timeline)
    queue_engine = QueueEngine(venue, timeline)

    state = {
        "venue": venue,
        "timeline": timeline,
        "crowd_engine": crowd_engine,
        "queue_engine": queue_engine,
        "alerts": [],
    }

    # Warm up simulation with 3 initial ticks
    for _ in range(3):
        timeline.tick()
        crowd_engine.tick()
        queue_engine.tick()

    logger.info(f"Simulation ready for {venue.name}")
    return state


# ── App Lifecycle ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.
    Ensures background tasks are cleaned up to prevent memory leaks.
    """
    global sim_state

    # 1. Startup Logic
    log_event("app_startup", {
        "venue_capacity": settings.VENUE_CAPACITY,
        "model": settings.GEMINI_MODEL,
        "has_gemini": settings.has_gemini
    })

    # Initialize simulation and share state with API routes
    sim_state = init_simulation()
    set_simulation_state(sim_state)

    # 2. Start Background Broadcaster
    broadcast_task = asyncio.create_task(
        simulation_broadcast_loop(sim_state, interval=2.0)
    )

    yield

    # 3. Shutdown Logic
    logger.info("Shutting down VenueFlow AI...")
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    
    log_event("app_shutdown", {"status": "success"})


# ── Create App ────────────────────────────────────────────────

app = FastAPI(
    title="VenueFlow AI",
    description="Enterprise-grade smart venue experience platform powered by Gemini.",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# ── Error Handling ────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions to prevent sensitive internal leakage."""
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Our engineering team has been notified."}
    )


# ── Middleware ────────────────────────────────────────────────

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [f"http://localhost:{settings.PORT}"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────

app.include_router(api_router)

# ── WebSocket ─────────────────────────────────────────────────

app.add_api_websocket_route("/ws", websocket_endpoint)

# ── Static Files ──────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the single-page application entry point."""
    return FileResponse(str(static_dir / "index.html"))
