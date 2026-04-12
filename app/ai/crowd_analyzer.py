"""
VenueFlow AI — Crowd Analyzer (AI-Powered Predictions)
Uses Gemini to analyze crowd patterns and predict surges.
Generates natural language insights for both attendees and operators.
"""
import json
import re
from typing import Dict, List, Optional

from app.config import settings

_client = None

def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


CROWD_ANALYSIS_PROMPT = """You are a crowd dynamics analyst for VenueFlow AI at Titan Arena (50,000 capacity).

Analyze the following crowd data and provide actionable insights.

CURRENT CROWD STATE:
{crowd_data}

EVENT PHASE: {event_phase} — {phase_description}
ELAPSED TIME: {elapsed_time}

Provide a JSON response:
{{
  "risk_level": "low" | "moderate" | "high" | "critical",
  "insights": ["insight 1", "insight 2", "insight 3"],
  "predictions": ["will happen in 15 min", "expect crowd shift"],
  "recommendations": ["for operator 1", "for operator 2"],
  "crowd_health_score": 0-100
}}

Focus on:
1. Identifying current bottlenecks
2. Predicting crowd movements in next 15 minutes based on event phase
3. Recommending proactive measures (open gate, redirect, deploy staff)"""


def analyze_crowd(
    crowd_data: str,
    event_phase: str,
    phase_description: str,
    elapsed_time: str,
    danger_zones: List[Dict],
) -> Dict:
    """
    Use Gemini to perform deep crowd analysis.
    Returns structured insights and predictions.
    """
    if not settings.has_gemini:
        return _generate_fallback_analysis(danger_zones, event_phase)

    try:
        prompt = CROWD_ANALYSIS_PROMPT.format(
            crowd_data=crowd_data,
            event_phase=event_phase,
            phase_description=phase_description,
            elapsed_time=elapsed_time,
        )
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
        text = response.text
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
        match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text.strip())
    except Exception:
        return _generate_fallback_analysis(danger_zones, event_phase)


def _generate_fallback_analysis(danger_zones: List[Dict], event_phase: str) -> Dict:
    """Rule-based fallback analysis."""
    has_danger = len(danger_zones) > 0
    risk = "high" if has_danger else "moderate" if event_phase in ["near_kickoff", "halftime", "post_event"] else "low"

    insights = []
    predictions = []
    recommendations = []

    if has_danger:
        for dz in danger_zones[:3]:
            insights.append(f"{dz['name']} is at {dz['density']:.0%} capacity — approaching critical density")
        recommendations.append("Deploy additional staff to congested zones")
        recommendations.append("Consider opening overflow gates")

    phase_insights = {
        "pre_event": {
            "insights": ["Fans are beginning to arrive. Entry flow is normal."],
            "predictions": ["Expect Gate A congestion in 20 minutes as main rush begins."],
            "recommendations": ["Ensure all food stalls are staffed and ready."],
        },
        "near_kickoff": {
            "insights": ["Peak arrival wave in progress. Most gates at high throughput."],
            "predictions": ["Gate congestion will ease within 10 minutes of kickoff."],
            "recommendations": ["Direct latecomers to Gate F (west) which has lower traffic."],
        },
        "halftime": {
            "insights": ["Halftime rush — massive movement to concourse areas."],
            "predictions": ["Food and restroom queues will peak in 5 minutes."],
            "recommendations": ["Open additional service counters. Deploy washroom attendants."],
        },
        "post_event": {
            "insights": ["Mass departure in progress. Exit gates under pressure."],
            "predictions": ["Exit congestion will last 20-30 minutes. Parking lot traffic heavy."],
            "recommendations": ["Stagger exit messaging by zone. Keep emergency exits accessible."],
        },
    }

    phase_data = phase_insights.get(event_phase, {
        "insights": ["Crowd levels are stable. No immediate concerns."],
        "predictions": ["No significant crowd changes expected in the next 15 minutes."],
        "recommendations": ["Maintain normal staffing levels."],
    })

    insights.extend(phase_data.get("insights", []))
    predictions.extend(phase_data.get("predictions", []))
    recommendations.extend(phase_data.get("recommendations", []))

    health_map = {"low": 85, "moderate": 65, "high": 40, "critical": 15}

    return {
        "risk_level": risk,
        "insights": insights[:4],
        "predictions": predictions[:3],
        "recommendations": recommendations[:3],
        "crowd_health_score": health_map.get(risk, 70),
    }
