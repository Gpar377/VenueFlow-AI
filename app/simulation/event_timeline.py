"""
VenueFlow AI — Event Timeline
Defines event phases and controls the simulation clock.
Each phase has different crowd behavior patterns.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EventPhase(str, Enum):
    """Phases of a sporting event."""
    PRE_EVENT = "pre_event"          # Gates open, fans arriving
    EARLY_ARRIVAL = "early_arrival"  # 60-30 min before kickoff
    NEAR_KICKOFF = "near_kickoff"    # 30-0 min before, rush hour
    FIRST_HALF = "first_half"        # Game in progress
    HALFTIME = "halftime"            # Break — mass movement to food/restrooms
    SECOND_HALF = "second_half"      # Game in progress
    FINAL_MINUTES = "final_minutes"  # Last 10 min — early leavers
    POST_EVENT = "post_event"        # Mass exodus
    EMERGENCY = "emergency"          # Manual override: evacuation


@dataclass
class PhaseConfig:
    """Behavior parameters for each event phase."""
    phase: EventPhase
    label: str
    duration_minutes: int
    arrival_rate: float        # 0.0–1.0 — how fast people stream in
    departure_rate: float      # 0.0–1.0 — how fast people leave
    concourse_activity: float  # 0.0–1.0 — movement to food/restrooms
    seat_occupancy_target: float  # target fill ratio
    alert_probability: float   # chance of alerts per tick
    description: str


# Phase configurations — realistic behavior
PHASE_CONFIGS = {
    EventPhase.PRE_EVENT: PhaseConfig(
        phase=EventPhase.PRE_EVENT,
        label="🎟️ Gates Open",
        duration_minutes=60,
        arrival_rate=0.15,
        departure_rate=0.0,
        concourse_activity=0.3,
        seat_occupancy_target=0.1,
        alert_probability=0.02,
        description="Gates have opened. Early fans are arriving and exploring the venue.",
    ),
    EventPhase.EARLY_ARRIVAL: PhaseConfig(
        phase=EventPhase.EARLY_ARRIVAL,
        label="🚶 Fans Arriving",
        duration_minutes=30,
        arrival_rate=0.4,
        departure_rate=0.0,
        concourse_activity=0.5,
        seat_occupancy_target=0.35,
        alert_probability=0.03,
        description="Steady stream of fans entering. Concourse areas getting busy.",
    ),
    EventPhase.NEAR_KICKOFF: PhaseConfig(
        phase=EventPhase.NEAR_KICKOFF,
        label="⚡ Rush Hour",
        duration_minutes=30,
        arrival_rate=0.85,
        departure_rate=0.0,
        concourse_activity=0.7,
        seat_occupancy_target=0.8,
        alert_probability=0.08,
        description="Peak arrival wave! Gates are congested. Concourses are packed.",
    ),
    EventPhase.FIRST_HALF: PhaseConfig(
        phase=EventPhase.FIRST_HALF,
        label="⚽ First Half",
        duration_minutes=45,
        arrival_rate=0.05,
        departure_rate=0.0,
        concourse_activity=0.15,
        seat_occupancy_target=0.92,
        alert_probability=0.02,
        description="Match in progress. Most fans are seated. Concourses are quiet.",
    ),
    EventPhase.HALFTIME: PhaseConfig(
        phase=EventPhase.HALFTIME,
        label="🍔 Halftime Break",
        duration_minutes=20,
        arrival_rate=0.0,
        departure_rate=0.02,
        concourse_activity=0.85,
        seat_occupancy_target=0.55,
        alert_probability=0.06,
        description="HALFTIME! Massive rush to food stalls and restrooms. Queue times peak.",
    ),
    EventPhase.SECOND_HALF: PhaseConfig(
        phase=EventPhase.SECOND_HALF,
        label="⚽ Second Half",
        duration_minutes=45,
        arrival_rate=0.0,
        departure_rate=0.03,
        concourse_activity=0.2,
        seat_occupancy_target=0.85,
        alert_probability=0.02,
        description="Match resumes. Fans returning to seats. Some trickle departures.",
    ),
    EventPhase.FINAL_MINUTES: PhaseConfig(
        phase=EventPhase.FINAL_MINUTES,
        label="⏱️ Final Minutes",
        duration_minutes=10,
        arrival_rate=0.0,
        departure_rate=0.15,
        concourse_activity=0.4,
        seat_occupancy_target=0.7,
        alert_probability=0.05,
        description="Last 10 minutes. Some fans leaving early to beat traffic.",
    ),
    EventPhase.POST_EVENT: PhaseConfig(
        phase=EventPhase.POST_EVENT,
        label="🚗 Mass Exit",
        duration_minutes=45,
        arrival_rate=0.0,
        departure_rate=0.7,
        concourse_activity=0.6,
        seat_occupancy_target=0.1,
        alert_probability=0.04,
        description="Full-time whistle! Everyone heading for exits. Peak congestion at gates.",
    ),
    EventPhase.EMERGENCY: PhaseConfig(
        phase=EventPhase.EMERGENCY,
        label="🚨 EVACUATION",
        duration_minutes=0,
        arrival_rate=0.0,
        departure_rate=1.0,
        concourse_activity=0.9,
        seat_occupancy_target=0.0,
        alert_probability=1.0,
        description="EMERGENCY EVACUATION IN PROGRESS. All gates open. Proceed to nearest exit.",
    ),
}


PHASE_ORDER = [
    EventPhase.PRE_EVENT,
    EventPhase.EARLY_ARRIVAL,
    EventPhase.NEAR_KICKOFF,
    EventPhase.FIRST_HALF,
    EventPhase.HALFTIME,
    EventPhase.SECOND_HALF,
    EventPhase.FINAL_MINUTES,
    EventPhase.POST_EVENT,
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
        if phase == EventPhase.EMERGENCY:
            self.override_phase = EventPhase.EMERGENCY
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
