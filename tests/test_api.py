"""
VenueFlow AI — API Integration Tests
Refactored to initialize simulation state and match enterprise response schemas.
"""
from fastapi.testclient import TestClient
from app.main import app, init_simulation
from app.api.routes import set_simulation_state

client = TestClient(app)

# Initialize simulation state before running tests
sim_state = init_simulation()
set_simulation_state(sim_state)

def test_api_venue():
    """Check venue layout API."""
    response = client.get("/api/venue")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "capacity" in data

def test_api_crowd():
    """Check crowd density API."""
    response = client.get("/api/crowd")
    assert response.status_code == 200
    data = response.json()
    # Updated to match enterprise schema
    assert "total_occupancy" in data
    assert "heatmap" in data
    assert "danger_zones" in data

def test_api_queues():
    """Check queue board API."""
    response = client.get("/api/queues")
    assert response.status_code == 200
    data = response.json()
    # Updated to match enterprise schema (returns dict with metadata)
    assert "queues" in data
    assert isinstance(data["queues"], list)

def test_timeline_state():
    """Verify timeline engine initialization."""
    response = client.get("/api/timeline")
    assert response.status_code == 200
    data = response.json()
    assert "current_phase" in data

def test_emergency_trigger():
    """Verify emergency phase override."""
    response = client.post("/api/simulate/phase", json={"phase": "emergency"})
    assert response.status_code == 200
    data = response.json()
    # Updated to match enterprise schema
    assert data["jumped_to"] == "emergency"
    assert "timeline" in data
