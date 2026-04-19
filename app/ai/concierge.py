"""
VenueFlow AI — AI Concierge (Multi-Agent Orchestrator)
Routes user queries to specialized Gemini agents and returns contextual responses.
"""
import json
import re
from typing import Dict, Any, Optional, Tuple

from app.config import settings
from app.ai.prompts import (
    ORCHESTRATOR_PROMPT, NAVIGATOR_PROMPT,
    FOODIE_PROMPT, SAFETY_PROMPT, GENERAL_PROMPT,
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

    food_keywords = ["food", "eat", "hungry", "drink", "stall", "menu", "burger",
                     "pizza", "queue", "wait time", "restroom", "toilet", "bathroom",
                     "snack", "coffee", "chai", "noodle", "ice cream"]
    nav_keywords = ["where", "how to get", "direction", "gate", "exit", "parking",
                    "find", "locate", "seat", "zone", "way to", "entrance", "lot"]
    safety_keywords = ["crowd", "danger", "emergency", "medical", "help", "crush",
                       "first aid", "evacuation", "safety", "packed", "too many"]

    food_score = sum(1 for k in food_keywords if k in msg)
    nav_score = sum(1 for k in nav_keywords if k in msg)
    safety_score = sum(1 for k in safety_keywords if k in msg)

    if food_score > nav_score and food_score > safety_score:
        return "foodie", 0.7
    elif nav_score > food_score and nav_score > safety_score:
        return "navigator", 0.7
    elif safety_score > 0:
        return "safety", 0.7
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
        agent = "safety"
        confidence = 1.0
    else:
        agent, confidence = route_query(user_message)

    # Step 2: Build specialist prompt with full context
    if agent == "navigator":
        prompt = NAVIGATOR_PROMPT.format(venue_context=venue_context)
    elif agent == "foodie":
        stall_info = queue_info  # Queue info includes stall details
        prompt = FOODIE_PROMPT.format(stall_info=stall_info, queue_info=queue_info)
    elif agent == "safety":
        prompt = SAFETY_PROMPT.format(
            crowd_info=crowd_info,
            alerts_info=alerts_info,
            danger_zones=danger_zones,
        )
    else:
        prompt = GENERAL_PROMPT.format(
            venue_context=venue_context,
            queue_info=queue_info,
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
    """Rule-based fallback responses when Gemini is unavailable."""
    msg = user_message.lower()

    responses = {
        "navigator": "Head to the nearest concourse area for directional signage. "
                     "Gate A (North) and Gate E (South) are the main entrances. "
                     "Check the venue map for the shortest route to your destination.",
        "foodie": "There are 8 food stalls across all concourses. "
                  "During halftime, the West Concourse stalls (Noodle Bar, Chai & Snacks) "
                  "typically have shorter queues. Check the Queue Board for live wait times.",
        "safety": "Titan Arena is currently operating normally. "
                  "Emergency exits are available at Gate H (East). "
                  "First Aid stations are at North and South Concourses.",
        "general": "Welcome to Titan Arena! I'm your AI assistant. "
                   "I can help with directions, food recommendations, queue times, "
                   "and safety information. What do you need?",
    }

    return {
        "message": responses.get(agent, responses["general"]),
        "agent": agent,
        "confidence": 0.3,
        "user_zone": "unknown",
        "fallback": True,
    }
