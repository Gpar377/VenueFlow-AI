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

    def __init__(self, capacity: int = 50000):
        self.name = "Titan Arena"
        self.sport = "Multi-Sport Stadium"
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
        """Create 8 seating zones + 4 concourse zones."""
        zone_defs = [
            # Main stands (seating)
            ("north", "North Stand", 8000, "seating", ["ne", "nw", "concourse_n"], 250, 50),
            ("south", "South Stand", 8000, "seating", ["se", "sw", "concourse_s"], 250, 450),
            ("east", "East Wing", 6000, "seating", ["ne", "se", "concourse_e"], 450, 250),
            ("west", "West Wing", 6000, "seating", ["nw", "sw", "concourse_w"], 50, 250),
            # Corner sections
            ("ne", "North-East Corner", 3000, "seating", ["north", "east"], 400, 100),
            ("nw", "North-West Corner", 3000, "seating", ["north", "west"], 100, 100),
            ("se", "South-East Corner", 3000, "seating", ["south", "east"], 400, 400),
            ("sw", "South-West Corner", 3000, "seating", ["south", "west"], 100, 400),
            # Concourse areas (higher capacity, walkways)
            ("concourse_n", "North Concourse", 4000, "concourse", ["north", "ne", "nw"], 250, 20),
            ("concourse_s", "South Concourse", 4000, "concourse", ["south", "se", "sw"], 250, 480),
            ("concourse_e", "East Concourse", 3000, "concourse", ["east", "ne", "se"], 480, 250),
            ("concourse_w", "West Concourse", 3000, "concourse", ["west", "nw", "sw"], 20, 250),
        ]

        for zid, name, cap, ztype, adj, x, y in zone_defs:
            self.zones[zid] = Zone(
                id=zid, name=name, capacity=cap,
                zone_type=ztype, adjacent_zones=adj, x=x, y=y,
            )

    def _build_gates(self):
        """Create entry/exit gates linked to concourse zones."""
        gate_defs = [
            ("gate_a", "Gate A — Main Entrance", "concourse_n", 150, "entry"),
            ("gate_b", "Gate B — North-East", "concourse_n", 120, "entry"),
            ("gate_c", "Gate C — East Entry", "concourse_e", 120, "entry"),
            ("gate_d", "Gate D — South-East", "concourse_s", 100, "entry"),
            ("gate_e", "Gate E — South Main", "concourse_s", 150, "entry"),
            ("gate_f", "Gate F — West Entry", "concourse_w", 120, "entry"),
            ("gate_g", "Gate G — VIP Entrance", "concourse_w", 60, "entry"),
            ("gate_h", "Gate H — Emergency Exit", "concourse_e", 200, "emergency"),
        ]

        for gid, name, zone_id, cap, gtype in gate_defs:
            self.gates[gid] = Gate(
                id=gid, name=name, zone_id=zone_id,
                capacity_per_minute=cap, gate_type=gtype,
            )
            if zone_id in self.zones:
                self.zones[zone_id].gates.append(gid)

    def _build_service_points(self):
        """Create food stalls, restrooms, merchandise, and medical points."""
        service_defs = [
            # Food stalls
            ("food_1", "🍔 Burger Junction", "concourse_n", "food", 4, 2.5,
             ["Classic Burger", "Cheese Burger", "Veggie Burger", "Fries", "Onion Rings"], 250),
            ("food_2", "🍕 Pizza Corner", "concourse_n", "food", 3, 2.0,
             ["Margherita", "Pepperoni", "Veggie Supreme", "Garlic Bread"], 300),
            ("food_3", "🌮 Taco Stand", "concourse_e", "food", 3, 3.0,
             ["Chicken Taco", "Beef Taco", "Veggie Bowl", "Nachos"], 200),
            ("food_4", "🍦 Ice Cream Bar", "concourse_e", "food", 2, 4.0,
             ["Vanilla Cone", "Chocolate Sundae", "Mango Sorbet", "Milkshake"], 180),
            ("food_5", "🥤 Drinks Hub", "concourse_s", "food", 5, 5.0,
             ["Cola", "Lemonade", "Water", "Energy Drink", "Coffee", "Hot Chocolate"], 150),
            ("food_6", "🍗 BBQ Pit", "concourse_s", "food", 3, 1.5,
             ["BBQ Wings", "Pulled Pork", "Grilled Corn", "Coleslaw"], 350),
            ("food_7", "🍜 Noodle Bar", "concourse_w", "food", 3, 2.0,
             ["Ramen", "Stir-fry Noodles", "Spring Rolls", "Dumplings"], 280),
            ("food_8", "☕ Chai & Snacks", "concourse_w", "food", 2, 4.0,
             ["Masala Chai", "Samosa", "Vada Pav", "Pani Puri", "Bhel"], 120),
            # Restrooms
            ("restroom_1", "🚻 Restroom North-A", "concourse_n", "restroom", 8, 6.0, [], 0),
            ("restroom_2", "🚻 Restroom North-B", "concourse_n", "restroom", 6, 6.0, [], 0),
            ("restroom_3", "🚻 Restroom East", "concourse_e", "restroom", 6, 6.0, [], 0),
            ("restroom_4", "🚻 Restroom South", "concourse_s", "restroom", 8, 6.0, [], 0),
            ("restroom_5", "🚻 Restroom West", "concourse_w", "restroom", 6, 6.0, [], 0),
            # Merchandise
            ("merch_1", "🏆 Official Store", "concourse_n", "merchandise", 4, 1.5,
             ["Team Jersey", "Cap", "Scarf", "Keychain", "Poster"], 800),
            ("merch_2", "🧢 Fan Zone Shop", "concourse_s", "merchandise", 3, 1.5,
             ["T-Shirt", "Flag", "Wristband", "Mug", "Sticker Pack"], 500),
            # Medical
            ("medical_1", "🏥 First Aid — North", "concourse_n", "medical", 2, 8.0, [], 0),
            ("medical_2", "🏥 First Aid — South", "concourse_s", "medical", 2, 8.0, [], 0),
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
            ("lot_a", "Parking Lot A — North", "gate_a", 3000),
            ("lot_b", "Parking Lot B — East", "gate_c", 2500),
            ("lot_c", "Parking Lot C — South", "gate_e", 2500),
            ("lot_d", "Parking Lot D — West (VIP)", "gate_g", 1000),
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
