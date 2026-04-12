"""
VenueFlow AI — FastAPI Application
Main application: mounts routes, WebSocket, middleware, static files, and simulation loop.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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
    """Initialize the venue simulation."""
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

    # Run a few initial ticks to seed data
    for _ in range(3):
        timeline.tick()
        crowd_engine.tick()
        queue_engine.tick()

    return state


# ── App Lifecycle ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup and teardown for the application."""
    global sim_state

    # Startup
    settings.validate()
    print("\n" + "=" * 60)
    print("  [*] VenueFlow AI — Smart Venue Experience Platform")
    print("=" * 60)
    print(f"  [*] Venue: Titan Arena ({settings.VENUE_CAPACITY:,} capacity)")
    print(f"  [*] AI Model: {settings.GEMINI_MODEL}")
    print(f"  [*] Gemini API: {'(+) Connected' if settings.has_gemini else '(!) Not configured (fallback mode)'}")
    print(f"  [*] Google Maps: {'(+) Enabled' if settings.has_maps else '(!) SVG mode'}")
    print(f"  [*] Firebase: {'(+) Connected' if settings.has_firebase else '(!) Local mode'}")
    print("=" * 60)
    print(f"  [*] Open in browser: http://localhost:{settings.PORT}")
    print("=" * 60 + "\n")

    # Initialize simulation
    sim_state = init_simulation()
    set_simulation_state(sim_state)

    # Start background simulation loop
    broadcast_task = asyncio.create_task(
        simulation_broadcast_loop(sim_state, interval=2.0)
    )

    yield

    # Shutdown
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    print("\n  [*] VenueFlow AI shut down gracefully.\n")


# ── Create App ────────────────────────────────────────────────

app = FastAPI(
    title="VenueFlow AI",
    description="AI-powered smart venue experience platform for large-scale sporting events",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────

app.include_router(api_router)

# ── WebSocket ─────────────────────────────────────────────────

app.add_api_websocket_route("/ws", websocket_endpoint)

# ── Static Files ──────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_index():
    """Serve the main SPA."""
    return FileResponse(str(static_dir / "index.html"))
