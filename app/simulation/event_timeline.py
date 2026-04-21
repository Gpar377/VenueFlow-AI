"""
VenueFlow AI — Event Timeline
Defines event phases and controls the simulation clock.
Each phase has different crowd behavior patterns.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EventPhase(str, Enum):
    """Phases of Resort Operations."""
    MORNING_RUSH = "morning_rush"          # Breakfast, check-outs
    NORMAL_OPS = "normal_ops"              # Relaxing at pool, exploring
    LUNCH_PEAK = "lunch_peak"              # Lunch rush
    AFTERNOON_LULL = "afternoon_lull"      # Spa, excursions
    DINNER_SERVICE = "dinner_service"      # Dinner rush
    EVENING_EVENTS = "evening_events"      # Entertainment
    NIGHT_OPS = "night_ops"                # Quiet
    CRITICAL_EMERGENCY = "critical_emergency" # Manual override: evacuation


@dataclass
class PhaseConfig:
    """Behavior parameters for each resort phase."""
    phase: EventPhase
    label: str
    duration_minutes: int
    arrival_rate: float        # stream in from outside
    departure_rate: float      # stream out
    concourse_activity: float  # movement to restaurants/amenities
    seat_occupancy_target: float  # room/lounge target fill ratio
    alert_probability: float   # chance of alerts per tick
    description: str


# Phase configurations — realistic behavior
PHASE_CONFIGS = {
    EventPhase.MORNING_RUSH: PhaseConfig(
        phase=EventPhase.MORNING_RUSH,
        label="🌅 Morning Rush",
        duration_minutes=120,
        arrival_rate=0.1,
        departure_rate=0.2,
        concourse_activity=0.6,
        seat_occupancy_target=0.4,
        alert_probability=0.01,
        description="Check-outs and breakfast rush. Lobbies and restaurants are busy.",
    ),
    EventPhase.NORMAL_OPS: PhaseConfig(
        phase=EventPhase.NORMAL_OPS,
        label="🏖️ Normal Ops",
        duration_minutes=240,
        arrival_rate=0.3,
        departure_rate=0.1,
        concourse_activity=0.3,
        seat_occupancy_target=0.6,
        alert_probability=0.02,
        description="Guests exploring the resort. Pool area and lounges are active.",
    ),
    EventPhase.LUNCH_PEAK: PhaseConfig(
        phase=EventPhase.LUNCH_PEAK,
        label="🍔 Lunch Peak",
        duration_minutes=90,
        arrival_rate=0.1,
        departure_rate=0.0,
        concourse_activity=0.7,
        seat_occupancy_target=0.8,
        alert_probability=0.03,
        description="Peak lunch hour. Heavy congestion near food and beverage wings.",
    ),
    EventPhase.AFTERNOON_LULL: PhaseConfig(
        phase=EventPhase.AFTERNOON_LULL,
        label="🍹 Afternoon Lull",
        duration_minutes=180,
        arrival_rate=0.4,
        departure_rate=0.1,
        concourse_activity=0.2,
        seat_occupancy_target=0.9,
        alert_probability=0.02,
        description="Check-ins arriving. Corridors are quiet, rooms filling up.",
    ),
    EventPhase.DINNER_SERVICE: PhaseConfig(
        phase=EventPhase.DINNER_SERVICE,
        label="🍽️ Dinner Service",
        duration_minutes=120,
        arrival_rate=0.0,
        departure_rate=0.05,
        concourse_activity=0.8,
        seat_occupancy_target=0.5,
        alert_probability=0.04,
        description="Mass movement to dining areas and bars.",
    ),
    EventPhase.EVENING_EVENTS: PhaseConfig(
        phase=EventPhase.EVENING_EVENTS,
        label="🎉 Evening Events",
        duration_minutes=180,
        arrival_rate=0.0,
        departure_rate=0.0,
        concourse_activity=0.4,
        seat_occupancy_target=0.9,
        alert_probability=0.02,
        description="Concerts and resort entertainment. High density in event halls.",
    ),
    EventPhase.NIGHT_OPS: PhaseConfig(
        phase=EventPhase.NIGHT_OPS,
        label="🌙 Night Ops",
        duration_minutes=480,
        arrival_rate=0.0,
        departure_rate=0.0,
        concourse_activity=0.05,
        seat_occupancy_target=0.99,
        alert_probability=0.01,
        description="Most guests asleep. Essential corridors and security only.",
    ),
    EventPhase.CRITICAL_EMERGENCY: PhaseConfig(
        phase=EventPhase.CRITICAL_EMERGENCY,
        label="🚨 EVACUATION ALARM",
        duration_minutes=0,
        arrival_rate=0.0,
        departure_rate=1.0,
        concourse_activity=0.99,
        seat_occupancy_target=0.0,
        alert_probability=1.0,
        description="CRITICAL EMERGENCY. Evacuation protocol engaged. Directing guests to Assembly Points.",
    ),
}


PHASE_ORDER = [
    EventPhase.MORNING_RUSH,
    EventPhase.NORMAL_OPS,
    EventPhase.LUNCH_PEAK,
    EventPhase.AFTERNOON_LULL,
    EventPhase.DINNER_SERVICE,
    EventPhase.EVENING_EVENTS,
    EventPhase.NIGHT_OPS,
]


class EventTimeline:
    """
    Manages the progression of event phases over simulated time.
    """

    def __init__(self):
        self.elapsed_seconds: int = 0
        self.current_phase_index: int = 0
        self.phase_elapsed_seconds: int = 0
        self.is_finished: bool = False
        self.speed_multiplier: float = 10.0  # 10x real-time for demo
        self.override_phase: Optional[EventPhase] = None

    @property
    def current_phase(self) -> EventPhase:
        if self.override_phase:
            return self.override_phase
        return PHASE_ORDER[min(self.current_phase_index, len(PHASE_ORDER) - 1)]

    @property
    def current_config(self) -> PhaseConfig:
        return PHASE_CONFIGS[self.current_phase]

    @property
    def phase_progress(self) -> float:
        """Progress through current phase 0.0 to 1.0."""
        duration_sec = self.current_config.duration_minutes * 60
        if duration_sec == 0:
            return 1.0
        return min(1.0, self.phase_elapsed_seconds / duration_sec)

    @property
    def total_event_minutes(self) -> int:
        return sum(pc.duration_minutes for pc in PHASE_CONFIGS.values())

    @property
    def elapsed_minutes(self) -> float:
        return self.elapsed_seconds / 60

    @property
    def elapsed_display(self) -> str:
        """Human-friendly elapsed time string."""
        mins = int(self.elapsed_minutes)
        hours = mins // 60
        remaining = mins % 60
        if hours > 0:
            return f"{hours}h {remaining}m"
        return f"{remaining}m"

    def tick(self, real_seconds: int = 5) -> Optional[EventPhase]:
        """
        Advance the timeline by real_seconds * speed_multiplier.
        Returns the new EventPhase if a phase transition occurred, else None.
        """
        if self.is_finished and not self.override_phase:
            return None

        # Do not advance internal clock if we are in override mode
        if self.override_phase:
            return None

        sim_seconds = int(real_seconds * self.speed_multiplier)
        self.elapsed_seconds += sim_seconds
        self.phase_elapsed_seconds += sim_seconds

        # Check phase transition
        duration_sec = self.current_config.duration_minutes * 60
        if self.phase_elapsed_seconds >= duration_sec:
            self.phase_elapsed_seconds = 0
            self.current_phase_index += 1

            if self.current_phase_index >= len(PHASE_ORDER):
                self.current_phase_index = len(PHASE_ORDER) - 1
                self.is_finished = True
                return None

            return self.current_phase

        return None

    def get_state(self) -> dict:
        return {
            "current_phase": self.current_phase.value,
            "phase_label": self.current_config.label,
            "phase_description": self.current_config.description,
            "phase_progress": round(self.phase_progress, 3),
            "elapsed_minutes": round(self.elapsed_minutes, 1),
            "elapsed_display": self.elapsed_display,
            "total_event_minutes": self.total_event_minutes,
            "is_finished": self.is_finished,
            "speed_multiplier": self.speed_multiplier,
        }

    def set_speed(self, multiplier: float):
        """Set simulation speed (1x = real-time, 10x = 10x faster)."""
        self.speed_multiplier = max(1.0, min(60.0, multiplier))

    def jump_to_phase(self, phase: EventPhase):
        """Jump directly to a specific phase (for demo purposes)."""
        if phase == EventPhase.CRITICAL_EMERGENCY:
            self.override_phase = EventPhase.CRITICAL_EMERGENCY
            return
            
        self.override_phase = None
        if phase in PHASE_ORDER:
            self.current_phase_index = PHASE_ORDER.index(phase)
            self.phase_elapsed_seconds = 0
            # Recalculate elapsed seconds
            self.elapsed_seconds = sum(
                PHASE_CONFIGS[p].duration_minutes * 60
                for p in PHASE_ORDER[:self.current_phase_index]
            )
            self.is_finished = False
