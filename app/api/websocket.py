"""
VenueFlow AI — WebSocket Handler
Real-time push updates for crowd density, queues, and alerts.
"""
import asyncio
import json
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections and broadcasts updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, data: dict):
        """Send data to all connected clients."""
        if not self.active_connections:
            return

        message = json.dumps(data)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Global connection manager
ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """Handle individual WebSocket connections."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & handle client messages
            data = await websocket.receive_text()
            # Client can send commands like speed changes
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def simulation_broadcast_loop(sim_state: dict, interval: float = 2.0):
    """
    Background task that ticks the simulation and broadcasts updates.
    Runs every `interval` seconds.
    """
    while True:
        try:
            # Tick simulation
            new_phase = sim_state["timeline"].tick()
            crowd_result = sim_state["crowd_engine"].tick()
            queue_result = sim_state["queue_engine"].tick()

            # Build update payload
            timeline = sim_state["timeline"].get_state()
            heatmap = sim_state["crowd_engine"].get_heatmap_data()
            danger_zones = sim_state["crowd_engine"].get_danger_zones()
            queues = sim_state["queue_engine"].get_all_queues()

            update = {
                "type": "tick",
                "timeline": timeline,
                "crowd": {
                    "heatmap": heatmap,
                    "danger_zones": danger_zones,
                    "total_occupancy": sim_state["venue"].get_total_occupancy(),
                    "occupancy_percentage": sim_state["venue"].get_occupancy_percentage(),
                },
                "queues": queues,
                "gates": [g.to_dict() for g in sim_state["venue"].gates.values()],
            }

            # Add phase change event
            if new_phase:
                update["phase_change"] = {
                    "new_phase": new_phase.value,
                    "label": sim_state["timeline"].current_config.label,
                    "description": sim_state["timeline"].current_config.description,
                }

            # Add alert if danger zones detected
            if danger_zones:
                update["alert"] = {
                    "level": "warning",
                    "message": f"High crowd density detected in: {', '.join(dz['name'] for dz in danger_zones)}",
                    "zones": danger_zones,
                }

            await ws_manager.broadcast(update)

        except Exception as e:
            # Don't crash the loop on errors
            pass

        await asyncio.sleep(interval)
