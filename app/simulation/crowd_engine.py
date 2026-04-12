"""
VenueFlow AI — Crowd Simulation Engine
Time-based crowd density simulation with realistic movement patterns.
Generates real-time occupancy data for all venue zones.
"""
import random
import math
from typing import Dict, List, Optional, Tuple

from app.simulation.venue import Venue, Zone
from app.simulation.event_timeline import EventTimeline, EventPhase, PHASE_CONFIGS


class CrowdEngine:
    """
    Simulates crowd movement through the venue based on event phase.
    Updates zone occupancies, gate flows, and generates density heatmap data.
    """

    def __init__(self, venue: Venue, timeline: EventTimeline):
        self.venue = venue
        self.timeline = timeline
        self._tick_count = 0
        self._noise_seed = random.randint(0, 10000)

    def tick(self) -> Dict:
        """
        Advance crowd simulation by one tick.
        Returns a summary of changes.
        """
        self._tick_count += 1
        config = self.timeline.current_config
        phase = self.timeline.current_phase

        # Apply crowd behavior for current phase
        arrivals = self._simulate_arrivals(config)
        departures = self._simulate_departures(config)
        movements = self._simulate_internal_movement(config)
        self._update_gate_flows(config)

        # Apply natural noise for organic feel
        self._apply_noise()

        # Ensure bounds
        self._clamp_occupancies()

        return {
            "tick": self._tick_count,
            "phase": phase.value,
            "arrivals": arrivals,
            "departures": departures,
            "internal_movements": movements,
            "total_occupancy": self.venue.get_total_occupancy(),
            "occupancy_pct": self.venue.get_occupancy_percentage(),
        }

    def _simulate_arrivals(self, config) -> int:
        """Simulate fans arriving through gates."""
        if config.arrival_rate <= 0:
            return 0

        total_arrivals = 0
        for gate in self.venue.gates.values():
            if not gate.is_open or gate.gate_type == "emergency":
                continue

            # Base arrival rate scaled by phase
            base = gate.capacity_per_minute * config.arrival_rate
            # Add randomness
            actual = int(base * random.uniform(0.6, 1.3) / 12)  # per 5-second tick

            zone = self.venue.zones.get(gate.zone_id)
            if zone and zone.density < 0.95:
                zone.current_occupancy += actual
                total_arrivals += actual

        # Distribute from concourse to seating zones
        self._flow_to_seats(config)

        return total_arrivals

    def _simulate_departures(self, config) -> int:
        """Simulate fans leaving the venue."""
        if config.departure_rate <= 0:
            return 0

        total_departures = 0
        for zone in self.venue.zones.values():
            if zone.current_occupancy <= 0:
                continue

            departure_count = int(
                zone.current_occupancy * config.departure_rate * random.uniform(0.3, 1.0) / 12
            )
            departure_count = min(departure_count, zone.current_occupancy)
            zone.current_occupancy -= departure_count
            total_departures += departure_count

        # Update parking lot vehicles with departures
        for lot in self.venue.parking_lots.values():
            lot.current_vehicles = max(0, lot.current_vehicles - int(total_departures * 0.25))
            lot.exit_congestion = min(1.0, config.departure_rate * random.uniform(0.5, 1.2))

        return total_departures

    def _flow_to_seats(self, config):
        """Move people from concourse zones to seating zones."""
        seat_target = config.seat_occupancy_target

        for zone in self.venue.zones.values():
            if zone.zone_type != "seating":
                continue

            target_occ = int(zone.capacity * seat_target)
            if zone.current_occupancy < target_occ:
                # Find adjacent concourse zone
                for adj_id in zone.adjacent_zones:
                    adj = self.venue.zones.get(adj_id)
                    if adj and adj.zone_type == "concourse" and adj.current_occupancy > 0:
                        flow = min(
                            int((target_occ - zone.current_occupancy) * 0.1),
                            adj.current_occupancy
                        )
                        if flow > 0:
                            zone.current_occupancy += flow
                            adj.current_occupancy -= flow

    def _simulate_internal_movement(self, config) -> int:
        """Simulate movement between adjacent zones (e.g., to food, restrooms)."""
        total_moves = 0
        activity = config.concourse_activity

        if activity < 0.1:
            return 0

        for zone in list(self.venue.zones.values()):
            if zone.zone_type == "seating" and zone.current_occupancy > 100:
                # Some fans leave seats for concourse
                movers = int(zone.current_occupancy * activity * random.uniform(0.01, 0.04))
                if movers > 0:
                    for adj_id in zone.adjacent_zones:
                        adj = self.venue.zones.get(adj_id)
                        if adj and adj.zone_type == "concourse" and adj.density < 0.9:
                            actual = min(movers, zone.current_occupancy)
                            zone.current_occupancy -= actual
                            adj.current_occupancy += actual
                            total_moves += actual
                            break

        return total_moves

    def _update_gate_flows(self, config):
        """Update gate flow rates based on current phase."""
        for gate in self.venue.gates.values():
            if not gate.is_open:
                gate.current_flow_rate = 0
                continue

            if config.arrival_rate > 0:
                gate.current_flow_rate = int(
                    gate.capacity_per_minute * config.arrival_rate * random.uniform(0.5, 1.1)
                )
            elif config.departure_rate > 0:
                gate.current_flow_rate = int(
                    gate.capacity_per_minute * config.departure_rate * random.uniform(0.4, 1.0)
                )
            else:
                gate.current_flow_rate = int(gate.capacity_per_minute * 0.05 * random.uniform(0, 1))

    def _apply_noise(self):
        """Add organic variation to avoid robotic-looking numbers."""
        for zone in self.venue.zones.values():
            if zone.current_occupancy > 50:
                noise = random.randint(-15, 15)
                zone.current_occupancy += noise

    def _clamp_occupancies(self):
        """Ensure all values stay within valid bounds."""
        for zone in self.venue.zones.values():
            zone.current_occupancy = max(0, min(zone.capacity, zone.current_occupancy))

    def get_heatmap_data(self) -> List[Dict]:
        """Return density data for all zones — optimized for frontend rendering."""
        return [
            {
                "id": z.id,
                "name": z.name,
                "density": round(z.density, 3),
                "status": z.status,
                "occupancy": z.current_occupancy,
                "capacity": z.capacity,
                "x": z.x,
                "y": z.y,
                "zone_type": z.zone_type,
            }
            for z in self.venue.zones.values()
        ]

    def get_danger_zones(self, threshold: float = 0.85) -> List[Dict]:
        """Return zones above the danger threshold."""
        return [
            {"zone_id": z.id, "name": z.name, "density": z.density}
            for z in self.venue.zones.values()
            if z.density >= threshold
        ]

    def get_crowd_summary(self) -> str:
        """Natural language summary of current crowd state for AI agents."""
        total = self.venue.get_total_occupancy()
        pct = self.venue.get_occupancy_percentage()
        busiest = self.venue.get_busiest_zones(3)
        quietest = self.venue.get_quietest_zones(3)

        summary = f"Venue occupancy: {total:,} ({pct}% full). "
        summary += f"Busiest: {', '.join(f'{z.name} ({z.density:.0%})' for z in busiest)}. "
        summary += f"Quietest: {', '.join(f'{z.name} ({z.density:.0%})' for z in quietest)}."
        return summary
