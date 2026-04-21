"""
VenueFlow AI — Queue Simulation Engine
M/M/c queueing model for accurate wait-time prediction at service points.
"""
import random
import math
from typing import Dict, List

from app.simulation.venue import Venue, ServicePoint
from app.simulation.event_timeline import EventTimeline, EventPhase


class QueueEngine:
    """
    Simulates queue dynamics at all service points using M/M/c queueing theory.
    Updates queue lengths. Generates wait-time predictions.
    """

    def __init__(self, venue: Venue, timeline: EventTimeline):
        self.venue = venue
        self.timeline = timeline
        self._tick_count = 0
        # Track historical queue data for "best time to visit" predictions
        self._history: Dict[str, List[float]] = {
            sp_id: [] for sp_id in venue.service_points
        }
        self._peak_wait_times: Dict[str, float] = {
            sp_id: 0.0 for sp_id in venue.service_points
        }

    def tick(self) -> Dict:
        """Advance queue simulation by one tick."""
        self._tick_count += 1
        config = self.timeline.current_config
        phase = self.timeline.current_phase

        total_served = 0
        total_joined = 0

        for sp in self.venue.service_points.values():
            if not sp.is_open:
                sp.queue_length = 0
                continue

            # Calculate arrival rate based on nearby zone density and phase
            zone = self.venue.zones.get(sp.zone_id)
            zone_density = zone.density if zone else 0.3

            join_rate = self._calculate_join_rate(sp, zone_density, config)
            serve_rate = self._calculate_serve_rate(sp, config)

            # People joining queue
            new_arrivals = max(0, int(join_rate * random.uniform(0.5, 1.5)))
            total_joined += new_arrivals

            # People being served (leaving queue)
            served = min(sp.queue_length + new_arrivals, max(0, int(serve_rate * random.uniform(0.7, 1.2))))
            total_served += served

            # Update queue length
            sp.queue_length = max(0, sp.queue_length + new_arrivals - served)
            
            if phase == EventPhase.CRITICAL_EMERGENCY:
                sp.queue_length = max(0, sp.queue_length - int(sp.queue_length * 0.5))

            # Add noise for organic feel
            if sp.queue_length > 3:
                sp.queue_length += random.randint(-2, 2)
                sp.queue_length = max(0, sp.queue_length)

            # Track history
            self._history[sp.id].append(sp.wait_time_minutes)
            if len(self._history[sp.id]) > 100:
                self._history[sp.id] = self._history[sp.id][-100:]
            self._peak_wait_times[sp.id] = max(
                self._peak_wait_times[sp.id], sp.wait_time_minutes
            )

        return {
            "tick": self._tick_count,
            "total_in_queues": sum(sp.queue_length for sp in self.venue.service_points.values()),
            "total_served": total_served,
            "total_joined": total_joined,
        }

    def _calculate_join_rate(self, sp: ServicePoint, zone_density: float, config) -> float:
        """
        Calculate how many people join this queue per tick.
        Depends on: zone density, service type, event phase.
        """
        base_rates = {
            "food": 3.0,
            "restroom": 4.0,
            "merchandise": 1.0,
            "medical": 0.2,
        }
        base = base_rates.get(sp.service_type, 1.0)

        if config.phase == EventPhase.CRITICAL_EMERGENCY:
            return 0.0

        # Phase multiplier — peak hours = huge food rush
        phase_mult = config.concourse_activity

        # Zone density — more people nearby = more joiners
        density_mult = zone_density * 2.0

        return base * phase_mult * density_mult

    def _calculate_serve_rate(self, sp: ServicePoint, config) -> float:
        """
        Calculate how many people get served per tick.
        Slows down during rush periods (overwhelmed staff).
        """
        base = sp.servers * sp.service_rate / 12  # per 5-second tick

        # Stress factor — service slows when queues are huge
        if sp.queue_length > 30:
            base *= 0.8
        elif sp.queue_length > 50:
            base *= 0.6

        return base

    def get_all_queues(self) -> List[Dict]:
        """Return queue status for all service points."""
        return [
            {
                **sp.to_dict(),
                "best_time_prediction": self._predict_best_time(sp),
                "trend": self._get_trend(sp.id),
                "peak_wait": round(self._peak_wait_times.get(sp.id, 0), 1),
            }
            for sp in self.venue.service_points.values()
        ]

    def get_queues_by_type(self, service_type: str) -> List[Dict]:
        """Return queues filtered by type (food, restroom, etc.)."""
        return [
            q for q in self.get_all_queues()
            if q["service_type"] == service_type
        ]

    def get_shortest_queue(self, service_type: str) -> Dict:
        """Find the service point with the shortest wait time of a given type."""
        queues = [
            sp for sp in self.venue.service_points.values()
            if sp.service_type == service_type and sp.is_open
        ]
        if not queues:
            return {}
        shortest = min(queues, key=lambda sp: sp.wait_time_minutes)
        return shortest.to_dict()

    def _predict_best_time(self, sp: ServicePoint) -> str:
        """Predict when the queue will be shortest — simple heuristic."""
        phase = self.timeline.current_phase
        wt = sp.wait_time_minutes

        if phase == EventPhase.CRITICAL_EMERGENCY:
            return "EVACUATE IMMEDIATELY. DO NOT WAIT IN QUEUE."
        elif phase == EventPhase.LUNCH_PEAK:
            return "Wait 10-15 min — queues peak during lunch"
        elif phase == EventPhase.MORNING_RUSH:
            return "Busy morning — grab coffee early or wait"
        elif phase in [EventPhase.AFTERNOON_LULL, EventPhase.NORMAL_OPS]:
            return "Now is a great time — queues are short!"
        elif phase == EventPhase.DINNER_SERVICE and wt < 5:
            return "Good time — queue is short right now"
        elif wt > 15:
            return f"Queue is long ({wt:.0f} min). Try again in 10-15 min."
        elif wt < 3:
            return "Go now — almost no wait!"
        return "Moderate wait — acceptable"

    def _get_trend(self, sp_id: str) -> str:
        """Calculate if queue is growing, shrinking, or stable."""
        history = self._history.get(sp_id, [])
        if len(history) < 5:
            return "stable"

        recent = history[-5:]
        older = history[-10:-5] if len(history) >= 10 else history[:5]

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)

        if avg_recent > avg_older + 1:
            return "growing"
        elif avg_recent < avg_older - 1:
            return "shrinking"
        return "stable"

    def get_queue_summary(self) -> str:
        """Natural language summary for AI agents."""
        food_queues = [sp for sp in self.venue.service_points.values() if sp.service_type == "food"]
        restroom_queues = [sp for sp in self.venue.service_points.values() if sp.service_type == "restroom"]

        avg_food = sum(sp.wait_time_minutes for sp in food_queues) / max(1, len(food_queues))
        avg_restroom = sum(sp.wait_time_minutes for sp in restroom_queues) / max(1, len(restroom_queues))

        shortest_food = min(food_queues, key=lambda sp: sp.wait_time_minutes) if food_queues else None
        shortest_restroom = min(restroom_queues, key=lambda sp: sp.wait_time_minutes) if restroom_queues else None

        summary = f"Average food wait: {avg_food:.0f} min. Average restroom wait: {avg_restroom:.0f} min. "
        if shortest_food:
            summary += f"Shortest food queue: {shortest_food.name} ({shortest_food.wait_time_minutes:.0f} min). "
        if shortest_restroom:
            summary += f"Shortest restroom queue: {shortest_restroom.name} ({shortest_restroom.wait_time_minutes:.0f} min)."
        return summary
