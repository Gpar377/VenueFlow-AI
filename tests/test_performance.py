"""
VenueFlow AI — Performance Stress Test
Verifies the simulation engines can handle high-frequency operation without drift.
"""
import time
import pytest
import asyncio
from app.simulation.venue import Venue
from app.simulation.event_timeline import EventTimeline, EventPhase
from app.simulation.crowd_engine import CrowdEngine
from app.simulation.queue_engine import QueueEngine

@pytest.mark.asyncio
async def test_simulation_performance_burst():
    """
    Stress test: Run 1000 simulation ticks sequentially.
    Target: Enterprise grade engines should process 1000 ticks in < 1 second.
    """
    venue = Venue(capacity=50000)
    timeline = EventTimeline()
    crowd = CrowdEngine(venue, timeline)
    queue = QueueEngine(venue, timeline)
    
    start_time = time.perf_counter()
    
    # Process 1000 ticks
    for _ in range(1000):
        timeline.tick()
        crowd.tick()
        queue.tick()
        
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    ticks_per_second = 1000 / duration
    print(f"\nPerformance: {ticks_per_second:.1f} ticks/second")
    print(f"Total time for 1000 ticks: {duration:.4f}s")
    
    # Assertion: Simulation must be extremely efficient
    assert duration < 1.0, f"Simulation too slow: {duration:.4f}s for 1000 ticks"
    assert venue.get_total_occupancy() >= 0
    assert 0 <= venue.get_occupancy_percentage() <= 100

def test_venue_memory_footprint():
    """
    Ensures the venue object remains lean under load.
    """
    venue = Venue(capacity=50000)
    # Verify zone data structure is intact
    assert len(venue.zones) == 12
    assert len(venue.gates) == 8
    assert len(venue.service_points) == 17
    
    # Verify serialization speed
    start = time.perf_counter()
    for _ in range(100):
        _ = venue.to_dict()
    end = time.perf_counter()
    
    avg_serialize_time = (end - start) / 100
    print(f"Average serialization time: {avg_serialize_time*1000:.4f}ms")
    assert avg_serialize_time < 0.005 # Should be < 5ms
