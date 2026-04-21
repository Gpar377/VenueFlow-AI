"""
VenueFlow AI — AI Concierge (Multi-Agent Orchestrator)
Routes user queries to specialized Gemini agents and returns contextual responses.
"""
import json
import re
from typing import Dict, Any, Optional, Tuple

from app.config import settings
from app.ai.prompts import (
    ORCHESTRATOR_PROMPT, EVAC_COMMANDER_PROMPT,
    RESOURCE_COORDINATOR_PROMPT, CRISIS_DIRECTOR_PROMPT, GENERAL_PROMPT,
)

# Lazy Gemini client
_client = None

def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _parse_json_response(text: str) -> Dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def _call_gemini(prompt: str) -> str:
    """Make a Gemini API call with error handling."""
    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {str(e)}")


def route_query(user_message: str) -> Tuple[str, float]:
    """
    Use the orchestrator agent to determine which specialist to route to.
    Returns (agent_name, confidence).
    """
    if not settings.has_gemini:
        return _rule_based_routing(user_message)

    try:
        prompt = f"{ORCHESTRATOR_PROMPT}\n\nUser query: \"{user_message}\""
        response = _call_gemini(prompt)
        result = _parse_json_response(response)
        return result.get("agent", "general"), result.get("confidence", 0.5)
    except Exception:
        return _rule_based_routing(user_message)


def _rule_based_routing(message: str) -> Tuple[str, float]:
    """Fallback rule-based routing when AI is unavailable."""
    msg = message.lower()

    resource_keywords = ["water", "food", "help", "doctor", "bleeding", "first aid", "shelter",
                     "bandage", "medical", "injury", "triage", "safe"]
    evac_keywords = ["where", "how to get", "direction", "exit", "stair", "stairwell",
                    "find", "locate", "leave", "assembly", "way out", "door", "run"]
    crisis_keywords = ["fire", "shooter", "smoke", "earthquake", "danger", "emergency", "collapse",
                       "alarm", "warning", "trapped", "help me"]

    resource_score = sum(1 for k in resource_keywords if k in msg)
    evac_score = sum(1 for k in evac_keywords if k in msg)
    crisis_score = sum(1 for k in crisis_keywords if k in msg)

    if crisis_score > 0:
        return "crisis_director", 0.9
    elif evac_score > resource_score and evac_score > crisis_score:
        return "evac_commander", 0.7
    elif resource_score > evac_score and resource_score > crisis_score:
        return "resource_coordinator", 0.7
    return "general", 0.5


def get_ai_response(
    user_message: str,
    venue_context: str,
    queue_info: str,
    crowd_info: str,
    event_info: str,
    alerts_info: str = "No active alerts.",
    danger_zones: str = "No danger zones detected.",
    user_zone: str = "unknown",
    is_emergency: bool = False,
) -> Dict[str, Any]:
    """
    Main entry point — processes a user message through the multi-agent system.
    Returns structured response with agent info and message.
    """
    # Step 1: Route the query
    if is_emergency:
        agent = "crisis_director"
        confidence = 1.0
    else:
        agent, confidence = route_query(user_message)

    # Step 2: Build specialist prompt with full context
    if agent == "evac_commander":
        prompt = EVAC_COMMANDER_PROMPT.format(venue_context=venue_context)
    elif agent == "resource_coordinator":
        resource_info = queue_info  # In crisis mode, queue_info represents triage queues
        prompt = RESOURCE_COORDINATOR_PROMPT.format(resource_info=resource_info)
    elif agent == "crisis_director":
        prompt = CRISIS_DIRECTOR_PROMPT.format(
            crowd_info=crowd_info,
            alerts_info=alerts_info,
            danger_zones=danger_zones,
        )
    else:
        prompt = GENERAL_PROMPT.format(
            venue_context=venue_context,
            resource_info=queue_info,
            event_info=event_info,
        )

    # Step 3: Call specialist
    full_prompt = f"{prompt}\n\nUser is currently in zone: {user_zone}\nUser asks: \"{user_message}\""

    if not settings.has_gemini:
        return _get_fallback_response(user_message, agent, venue_context, queue_info)

    try:
        response_text = _call_gemini(full_prompt)
        return {
            "message": response_text.strip(),
            "agent": agent,
            "confidence": confidence,
            "user_zone": user_zone,
        }
    except Exception as e:
        return _get_fallback_response(user_message, agent, venue_context, queue_info)


def _get_fallback_response(
    user_message: str, agent: str,
    venue_context: str, queue_info: str,
) -> Dict[str, Any]:
    """Rule-based fallback responses when Gemini network is unavailable (Catastrophic Network Failure)."""
    msg = user_message.lower()

    responses = {
        "evac_commander": "NETWORK OFFLINE. Proceed immediately to the nearest illuminated stairwell. DO NOT USE ELEVATORS. Follow exit signs to the ground floor Assembly Points.",
        "resource_coordinator": "NETWORK OFFLINE. Central Triage is located in the Grand Lobby. If you cannot reach the lobby safely, shelter in place and block your door against smoke.",
        "crisis_director": "CRITICAL ALERT: NETWORK OFFLINE. An emergency has been detected at Grand Horizon Resort. Evacuate immediately via stairs or shelter in place if corridors are hot or filled with smoke.",
        "general": "NETWORK OFFLINE. The resort is under an active emergency protocol. Please evacuate via the nearest stairs or seek safety.",
    }

    return {
        "message": responses.get(agent, responses["general"]),
        "agent": agent,
        "confidence": 0.99,
        "user_zone": "unknown",
        "fallback": True,
    }
