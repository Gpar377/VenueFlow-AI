"""
VenueFlow AI — WebSocket Handler
Real-time push updates for crowd density, queues, and alerts.
Optimized for enterprise reliability with error logging and heartbeats.
"""
import asyncio
import json
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect
from app.logger import logger


class ConnectionManager:
    """Manages WebSocket connections and broadcasts updates safely."""

    def __init__(self):
        # Using a set for O(1) membership operations
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accepts and tracks a new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.debug(f"Client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Removes a connection from tracked set."""
        self.active_connections.discard(websocket)
        logger.debug(f"Client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """
        Sends JSON-serialized data to all active clients.
        Handles individual connection failures without crashing the broadcast.
        """
        if not self.active_connections:
            return

        message = json.dumps(data)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client {id(connection)}: {str(e)}")
                disconnected.add(connection)

        # Cleanup failed connections
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager instance
ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    Handle individual WebSocket connection lifecycle.
    Implements a simple ping/pong heartbeat to keep connections alive through proxies.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Awaiting client messages or heartbeats
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for client {id(websocket)}: {str(e)}")
        ws_manager.disconnect(websocket)


async def simulation_broadcast_loop(sim_state: dict, interval: float = 2.0):
    """
    Background simulation loop.
    Ticks simulation engines and broadcasts the global state to all connected clients.
    """
    logger.info(f"Starting simulation broadcast loop (Interval: {interval}s)")
    while True:
        try:
            # 1. Tick simulation engines
            # In a heavy enterprise app, these might run in separate threads
            new_phase = sim_state["timeline"].tick()
            sim_state["crowd_engine"].tick()
            sim_state["queue_engine"].tick()

            # 2. Extract current state
            venue = sim_state["venue"]
            timeline = sim_state["timeline"].get_state()
            heatmap = sim_state["crowd_engine"].get_heatmap_data()
            danger_zones = sim_state["crowd_engine"].get_danger_zones()
            queues = sim_state["queue_engine"].get_all_queues()

            # 3. Build optimized payload
            update = {
                "type": "tick",
                "timeline": timeline,
                "crowd": {
                    "heatmap": heatmap,
                    "danger_zones": danger_zones,
                    "total_occupancy": venue.get_total_occupancy(),
                    "occupancy_percentage": venue.get_occupancy_percentage(),
                },
                "queues": queues,
                "gates": [g.to_dict() for g in venue.gates.values()],
            }

            # 4. Inject phase events
            if new_phase:
                update["phase_change"] = {
                    "new_phase": new_phase.value,
                    "label": sim_state["timeline"].current_config.label,
                    "description": sim_state["timeline"].current_config.description,
                }

            # 5. Inject crowd priority alerts
            if danger_zones:
                update["alert"] = {
                    "level": "warning",
                    "message": f"High crowd density detected in: {', '.join(dz['name'] for dz in danger_zones)}",
                    "zones": danger_zones,
                }

            # 6. Push to clients
            await ws_manager.broadcast(update)

        except Exception as e:
            logger.error(f"Error in simulation broadcast loop: {str(e)}", exc_info=True)

        await asyncio.sleep(interval)
