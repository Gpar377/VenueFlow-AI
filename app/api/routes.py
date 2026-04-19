"""
VenueFlow AI — REST API Routes
All HTTP endpoints for the venue assistant platform.
"""
import random
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.security import sanitize_input

router = APIRouter(prefix="/api", tags=["VenueFlow API"])


# ── Request / Response Models ─────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    user_zone: str = Field(default="unknown")

class ChatResponse(BaseModel):
    message: str
    agent: str
    confidence: float
    user_zone: str
    fallback: bool = False

class SimulateRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=50)

class PhaseJumpRequest(BaseModel):
    phase: str


# ── Dependency: get simulation state ──────────────────────────
# These will be set by main.py on startup
_sim_state = None

def set_simulation_state(state):
    global _sim_state
    _sim_state = state

def _get_sim():
    if _sim_state is None:
        raise HTTPException(status_code=503, detail="Simulation not initialized")
    return _sim_state


# ── Monitoring & Health ───────────────────────────────────────

@router.get("/health")
async def health_check():
    """Liveness probe for Cloud Run / K8s."""
    return {"status": "alive", "service": "venueflow-ai"}

@router.get("/ready")
async def readiness_probe():
    """Readiness probe verifying simulation state."""
    sim = _get_sim()
    if not sim:
        raise HTTPException(status_code=503, detail="Simulation not ready")
    return {"status": "ready", "venue": sim["venue"].name}


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/venue")
async def get_venue():
    """Get complete venue layout and current state."""
    sim = _get_sim()
    return sim["venue"].to_dict()


@router.get("/crowd")
async def get_crowd():
    """Get real-time crowd density data for all zones."""
    sim = _get_sim()
    return {
        "heatmap": sim["crowd_engine"].get_heatmap_data(),
        "danger_zones": sim["crowd_engine"].get_danger_zones(),
        "total_occupancy": sim["venue"].get_total_occupancy(),
        "occupancy_percentage": sim["venue"].get_occupancy_percentage(),
        "summary": sim["crowd_engine"].get_crowd_summary(),
    }


@router.get("/queues")
async def get_queues(service_type: Optional[str] = Query(None)):
    """Get queue wait times for all service points."""
    sim = _get_sim()
    if service_type:
        queues = sim["queue_engine"].get_queues_by_type(service_type)
    else:
        queues = sim["queue_engine"].get_all_queues()
    return {
        "queues": queues,
        "summary": sim["queue_engine"].get_queue_summary(),
    }


@router.get("/queues/shortest")
async def get_shortest_queue(service_type: str = Query("food")):
    """Find the service point with the shortest wait time."""
    sim = _get_sim()
    result = sim["queue_engine"].get_shortest_queue(service_type)
    if not result:
        raise HTTPException(status_code=404, detail=f"No open {service_type} service points")
    return result


@router.get("/alerts")
async def get_alerts():
    """Get active alerts and crowd analysis."""
    sim = _get_sim()
    from app.ai.crowd_analyzer import analyze_crowd

    crowd_data = sim["crowd_engine"].get_crowd_summary()
    timeline_state = sim["timeline"].get_state()
    danger_zones = sim["crowd_engine"].get_danger_zones()

    analysis = analyze_crowd(
        crowd_data=crowd_data,
        event_phase=timeline_state["current_phase"],
        phase_description=timeline_state["phase_description"],
        elapsed_time=timeline_state["elapsed_display"],
        danger_zones=danger_zones,
    )

    return {
        "analysis": analysis,
        "danger_zones": danger_zones,
        "active_alerts": sim.get("alerts", []),
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the AI concierge."""
    from app.ai.concierge import get_ai_response

    sim = _get_sim()

    # Sanitize input
    clean_message = sanitize_input(request.message)
    if not clean_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Build context strings for AI agents
    venue_context = sim["crowd_engine"].get_crowd_summary()
    queue_info = sim["queue_engine"].get_queue_summary()
    crowd_info = sim["crowd_engine"].get_crowd_summary()
    timeline_state = sim["timeline"].get_state()
    event_info = f"Phase: {timeline_state['phase_label']} | {timeline_state['phase_description']}"

    danger_zones = sim["crowd_engine"].get_danger_zones()
    danger_info = ", ".join(f"{dz['name']} ({dz['density']:.0%})" for dz in danger_zones) or "None"
    
    is_emergency = timeline_state['current_phase'] == "emergency"

    response = get_ai_response(
        user_message=clean_message,
        venue_context=venue_context,
        queue_info=queue_info,
        crowd_info=crowd_info,
        event_info=event_info,
        danger_zones=danger_info,
        user_zone=request.user_zone,
        is_emergency=is_emergency,
    )

    return ChatResponse(**response)


@router.get("/timeline")
async def get_timeline():
    """Get current event timeline state."""
    sim = _get_sim()
    return sim["timeline"].get_state()


@router.post("/simulate/tick")
async def simulate_tick(request: SimulateRequest):
    """Advance the simulation by N ticks."""
    sim = _get_sim()
    results = []
    phase_changed = None

    for _ in range(request.ticks):
        new_phase = sim["timeline"].tick()
        if new_phase:
            phase_changed = new_phase.value
        crowd_result = sim["crowd_engine"].tick()
        queue_result = sim["queue_engine"].tick()
        results.append({"crowd": crowd_result, "queue": queue_result})

    return {
        "ticks_processed": request.ticks,
        "phase_changed": phase_changed,
        "timeline": sim["timeline"].get_state(),
        "crowd_summary": sim["crowd_engine"].get_crowd_summary(),
        "total_occupancy": sim["venue"].get_total_occupancy(),
        "occupancy_percentage": sim["venue"].get_occupancy_percentage(),
    }


@router.post("/simulate/phase")
async def jump_to_phase(request: PhaseJumpRequest):
    """Jump to a specific event phase (for demo)."""
    from app.simulation.event_timeline import EventPhase
    sim = _get_sim()

    try:
        phase = EventPhase(request.phase)
    except ValueError:
        valid = [p.value for p in EventPhase]
        raise HTTPException(status_code=400, detail=f"Invalid phase. Valid: {valid}")

    sim["timeline"].jump_to_phase(phase)

    # Run a few ticks to populate the new phase
    for _ in range(5):
        sim["crowd_engine"].tick()
        sim["queue_engine"].tick()

    return {
        "jumped_to": phase.value,
        "timeline": sim["timeline"].get_state(),
        "occupancy_percentage": sim["venue"].get_occupancy_percentage(),
    }


@router.post("/simulate/speed")
async def set_speed(speed: float = Query(10.0, ge=1.0, le=60.0)):
    """Set simulation speed multiplier."""
    sim = _get_sim()
    sim["timeline"].set_speed(speed)
    return {"speed_multiplier": speed}


@router.get("/stats")
async def get_stats():
    """Get operator dashboard statistics."""
    sim = _get_sim()
    venue = sim["venue"]
    timeline = sim["timeline"].get_state()

    zones = venue.zones
    gates = venue.gates
    services = venue.service_points

    return {
        "venue_name": venue.name,
        "capacity": venue.capacity,
        "total_occupancy": venue.get_total_occupancy(),
        "occupancy_percentage": venue.get_occupancy_percentage(),
        "event_phase": timeline,
        "zones_by_density": sorted(
            [z.to_dict() for z in zones.values()],
            key=lambda z: z["density"],
            reverse=True,
        ),
        "gates": [g.to_dict() for g in gates.values()],
        "service_summary": {
            "food_stalls": len([s for s in services.values() if s.service_type == "food"]),
            "avg_food_wait": round(
                sum(s.wait_time_minutes for s in services.values() if s.service_type == "food")
                / max(1, len([s for s in services.values() if s.service_type == "food"])), 1
            ),
            "total_in_queues": sum(s.queue_length for s in services.values()),
        },
        "parking": [p.to_dict() for p in venue.parking_lots.values()],
    }


@router.get("/exit-strategy")
async def get_exit_strategy(zone: str = Query("north"), parking: str = Query("lot_a")):
    """Get personalized exit strategy based on user's zone and parking lot."""
    sim = _get_sim()
    venue = sim["venue"]

    user_zone = venue.zones.get(zone)
    user_parking = venue.parking_lots.get(parking)

    if not user_zone:
        raise HTTPException(status_code=404, detail=f"Unknown zone: {zone}")

    # Find the best gate based on zone and parking
    best_gate = None
    if user_parking:
        best_gate = venue.gates.get(user_parking.nearest_gate)

    # Calculate alternative routes
    all_gates = sorted(
        [g for g in venue.gates.values() if g.is_open and g.gate_type != "emergency"],
        key=lambda g: g.congestion,
    )

    recommended_gate = best_gate if best_gate and best_gate.congestion < 0.8 else all_gates[0]

    return {
        "user_zone": user_zone.to_dict(),
        "parking_lot": user_parking.to_dict() if user_parking else None,
        "recommended_gate": recommended_gate.to_dict(),
        "alternative_gates": [g.to_dict() for g in all_gates[:3]],
        "tip": f"Head to {recommended_gate.name} for the quickest exit. "
               f"Current congestion: {recommended_gate.congestion:.0%}. "
               f"{'Consider waiting 5 minutes for the rush to ease.' if recommended_gate.congestion > 0.6 else 'Path is relatively clear!'}",
    }
