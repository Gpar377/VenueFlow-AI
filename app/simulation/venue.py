"""
VenueFlow AI — Venue Model
Defines the complete stadium layout: zones, gates, stalls, restrooms, parking.
All data is synthetic — no external data required.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random
import math


@dataclass
class Zone:
    """
    Represents a discrete physical section of the stadium.
    
    Attributes:
        id (str): Unique identifier for the zone.
        name (str): Human-readable name.
        capacity (int): Maximum safe occupancy.
        current_occupancy (int): Current number of persons in zone.
        zone_type (str): Categorization (seating, concourse, etc).
        adjacent_zones (List[str]): List of neighbor zone IDs for flow modeling.
        gates (List[str]): List of associated gate IDs.
    """
    id: str
    name: str
    capacity: int
    current_occupancy: int = 0
    zone_type: str = "seating"  # seating, concourse, vip, field_level
    adjacent_zones: List[str] = field(default_factory=list)
    gates: List[str] = field(default_factory=list)
    x: float = 0.0  # SVG map coordinate
    y: float = 0.0

    @property
    def density(self) -> float:
        """Crowd density ratio 0.0 to 1.0."""
        if self.capacity == 0:
            return 0.0
        return min(1.0, max(0.0, self.current_occupancy / self.capacity))

    @property
    def status(self) -> str:
        d = self.density
        if d < 0.4:
            return "low"
        elif d < 0.7:
            return "moderate"
        elif d < 0.9:
            return "high"
        return "critical"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "current_occupancy": self.current_occupancy,
            "density": round(self.density, 3),
            "status": self.status,
            "zone_type": self.zone_type,
            "adjacent_zones": self.adjacent_zones,
            "gates": self.gates,
            "x": self.x,
            "y": self.y,
        }


@dataclass
class Gate:
    """
    Represents an entry, exit, or emergency portal.
    
    Calculates congestion based on current flow vs physical throughput capacity.
    """
    id: str
    name: str
    zone_id: str
    capacity_per_minute: int = 120
    is_open: bool = True
    current_flow_rate: int = 0  # people per minute currently
    gate_type: str = "entry"  # entry, exit, emergency

    @property
    def congestion(self) -> float:
        if self.capacity_per_minute == 0:
            return 0.0
        return min(1.0, self.current_flow_rate / self.capacity_per_minute)

    @property
    def status(self) -> str:
        if not self.is_open:
            return "closed"
        c = self.congestion
        if c < 0.5:
            return "clear"
        elif c < 0.8:
            return "busy"
        return "congested"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "zone_id": self.zone_id,
            "capacity_per_minute": self.capacity_per_minute,
            "is_open": self.is_open,
            "current_flow_rate": self.current_flow_rate,
            "congestion": round(self.congestion, 3),
            "status": self.status,
            "gate_type": self.gate_type,
        }


@dataclass
class ServicePoint:
    """
    Represents a point of interest where queues form (F&B, Restrooms, etc).
    
    Implements localized queueing theory (M/M/c) for wait time approximation.
    """
    id: str
    name: str
    zone_id: str
    service_type: str  # food, restroom, merchandise, medical
    servers: int = 3  # number of service counters
    service_rate: float = 2.0  # customers served per minute per server
    queue_length: int = 0
    is_open: bool = True
    menu_items: List[str] = field(default_factory=list)
    avg_price: float = 0.0

    @property
    def wait_time_minutes(self) -> float:
        """Estimated wait time using M/M/c approximation."""
        if not self.is_open or self.servers == 0:
            return 99.0
        if self.queue_length == 0:
            return 0.0
        total_service_rate = self.servers * self.service_rate
        if total_service_rate == 0:
            return 99.0
        return round(self.queue_length / total_service_rate, 1)

    @property
    def wait_status(self) -> str:
        wt = self.wait_time_minutes
        if wt < 3:
            return "short"
        elif wt < 8:
            return "moderate"
        elif wt < 15:
            return "long"
        return "very_long"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "zone_id": self.zone_id,
            "service_type": self.service_type,
            "servers": self.servers,
            "service_rate": self.service_rate,
            "queue_length": self.queue_length,
            "wait_time_minutes": self.wait_time_minutes,
            "wait_status": self.wait_status,
            "is_open": self.is_open,
            "menu_items": self.menu_items,
            "avg_price": self.avg_price,
        }


@dataclass
class ParkingLot:
    """A parking area with exit route info."""
    id: str
    name: str
    nearest_gate: str
    capacity: int = 2000
    current_vehicles: int = 0
    exit_congestion: float = 0.0

    @property
    def availability(self) -> float:
        if self.capacity == 0:
            return 0.0
        return max(0.0, 1.0 - (self.current_vehicles / self.capacity))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "nearest_gate": self.nearest_gate,
            "capacity": self.capacity,
            "current_vehicles": self.current_vehicles,
            "availability": round(self.availability, 3),
            "exit_congestion": round(self.exit_congestion, 3),
        }


class Venue:
    """
    The Digital Twin representation of the physical stadium.
    
    Orchestrates the relationship between seating zones, concourse zones,
    gates, and service points. Responsible for calculating aggregate metrics
    such as total occupancy and venue-wide density.
    """

    def __init__(self, capacity: int = 15000):
        self.name = "Grand Horizon Resort"
        self.sport = "Hospitality & Convention"
        self.capacity = capacity
        self.zones: Dict[str, Zone] = {}
        self.gates: Dict[str, Gate] = {}
        self.service_points: Dict[str, ServicePoint] = {}
        self.parking_lots: Dict[str, ParkingLot] = {}
        self._build()

    def _build(self):
        """Construct the entire venue layout."""
        self._build_zones()
        self._build_gates()
        self._build_service_points()
        self._build_parking()

    def _build_zones(self):
        """Create Resort Wings and Lobbies."""
        zone_defs = [
            # Main Guest Towers
            ("north_tower", "North Tower", 1800, "seating", ["grand_lobby", "pool_deck"], 250, 50),
            ("south_tower", "South Tower", 1800, "seating", ["grand_lobby", "pool_deck"], 250, 450),
            ("east_wing", "East Wing", 1200, "seating", ["grand_lobby", "conference_center"], 450, 250),
            ("west_wing", "West Wing (Spa)", 800, "seating", ["grand_lobby"], 50, 250),
            # Corridors & Amenities
            ("grand_lobby", "Grand Lobby", 3000, "concourse", ["north_tower", "south_tower", "east_wing", "west_wing", "pool_deck", "conference_center"], 250, 250),
            ("pool_deck", "Pool & Recreation", 1500, "concourse", ["grand_lobby", "north_tower", "south_tower"], 150, 250),
            ("conference_center", "Conference Center", 2500, "concourse", ["east_wing", "grand_lobby"], 400, 150),
            ("staff_quarters", "Staff & Maintenance", 500, "concourse", ["grand_lobby"], 100, 400),
        ]

        for zid, name, cap, ztype, adj, x, y in zone_defs:
            self.zones[zid] = Zone(
                id=zid, name=name, capacity=cap,
                zone_type=ztype, adjacent_zones=adj, x=x, y=y,
            )

    def _build_gates(self):
        """Create Exits and Elevators."""
        gate_defs = [
            ("gate_a", "Main Entrance (Lobby)", "grand_lobby", 150, "entry"),
            ("gate_b", "Poolside Exit", "pool_deck", 120, "entry"),
            ("gate_c", "Conference Center Entrance", "conference_center", 200, "entry"),
            ("gate_d", "North Stairwell Exit", "north_tower", 100, "emergency"),
            ("gate_e", "South Stairwell Exit", "south_tower", 100, "emergency"),
            ("gate_f", "East Wing Fire Escape", "east_wing", 80, "emergency"),
            ("gate_g", "Staff Entrance", "staff_quarters", 60, "entry"),
            ("gate_h", "Emergency Loading Dock", "staff_quarters", 200, "emergency"),
        ]

        for gid, name, zone_id, cap, gtype in gate_defs:
            self.gates[gid] = Gate(
                id=gid, name=name, zone_id=zone_id,
                capacity_per_minute=cap, gate_type=gtype,
            )
            if zone_id in self.zones:
                self.zones[zone_id].gates.append(gid)

    def _build_service_points(self):
        """Create restaurants, spa, merchandise, and medical triage."""
        service_defs = [
            # Dining
            ("food_1", "🍽️ Oceanview Restaurant", "grand_lobby", "food", 6, 2.5, ["Steak", "Lobster", "Wine"], 850),
            ("food_2", "🍹 Poolside Cabana Bar", "pool_deck", "food", 4, 4.0, ["Margarita", "Beer", "Snacks"], 300),
            ("food_3", "☕ Lobby Cafe", "grand_lobby", "food", 3, 5.0, ["Coffee", "Pastries"], 150),
            ("food_4", "🍱 Conference Banquet", "conference_center", "food", 8, 2.0, ["Buffet"], 500),
            ("food_5", "💆 Spa Lounge", "west_wing", "food", 2, 2.0, ["Smoothie", "Tea"], 200),
            # Restrooms
            ("restroom_1", "🚻 Lobby Restrooms", "grand_lobby", "restroom", 6, 6.0, [], 0),
            ("restroom_2", "🚻 Pool Restrooms", "pool_deck", "restroom", 4, 6.0, [], 0),
            ("restroom_3", "🚻 Conference Restrooms", "conference_center", "restroom", 8, 6.0, [], 0),
            # Retail
            ("merch_1", "👜 Boutique Shop", "grand_lobby", "merchandise", 3, 1.5, ["Clothes", "Souvenirs"], 1200),
            ("merch_2", "🏊‍♀️ Swim Shop", "pool_deck", "merchandise", 2, 2.0, ["Sunscreen", "Swimwear"], 400),
            # Medical / Safety Triage
            ("medical_1", "🏥 Central Triage (Lobby)", "grand_lobby", "medical", 4, 8.0, [], 0),
            ("medical_2", "🏥 Poolside First Aid", "pool_deck", "medical", 2, 8.0, [], 0),
        ]

        for spid, name, zone_id, stype, servers, rate, items, price in service_defs:
            self.service_points[spid] = ServicePoint(
                id=spid, name=name, zone_id=zone_id,
                service_type=stype, servers=servers,
                service_rate=rate, menu_items=items,
                avg_price=price,
            )

    def _build_parking(self):
        """Create parking lots."""
        parking_defs = [
            ("lot_a", "Valet Parking", "gate_a", 500),
            ("lot_b", "Self Parking Garage", "gate_a", 1500),
            ("lot_c", "Event & Conference Parking", "gate_c", 1000),
            ("lot_d", "Employee Parking", "gate_g", 300),
        ]
        for pid, name, gate, cap in parking_defs:
            self.parking_lots[pid] = ParkingLot(
                id=pid, name=name, nearest_gate=gate, capacity=cap,
            )

    def get_total_occupancy(self) -> int:
        """Total people currently in the venue."""
        return sum(z.current_occupancy for z in self.zones.values() if z.zone_type == "seating")

    def get_occupancy_percentage(self) -> float:
        """Venue fill percentage."""
        seating_cap = sum(z.capacity for z in self.zones.values() if z.zone_type == "seating")
        if seating_cap == 0:
            return 0.0
        return round(self.get_total_occupancy() / seating_cap * 100, 1)

    def get_zone_densities(self) -> Dict[str, float]:
        """Return density for all zones."""
        return {zid: z.density for zid, z in self.zones.items()}

    def get_busiest_zones(self, n: int = 3) -> List[Zone]:
        """Return top-N busiest zones."""
        return sorted(self.zones.values(), key=lambda z: z.density, reverse=True)[:n]

    def get_quietest_zones(self, n: int = 3) -> List[Zone]:
        """Return top-N least crowded zones."""
        return sorted(self.zones.values(), key=lambda z: z.density)[:n]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sport": self.sport,
            "capacity": self.capacity,
            "total_occupancy": self.get_total_occupancy(),
            "occupancy_percentage": self.get_occupancy_percentage(),
            "zones": {zid: z.to_dict() for zid, z in self.zones.items()},
            "gates": {gid: g.to_dict() for gid, g in self.gates.items()},
            "service_points": {sid: s.to_dict() for sid, s in self.service_points.items()},
            "parking_lots": {pid: p.to_dict() for pid, p in self.parking_lots.items()},
        }
