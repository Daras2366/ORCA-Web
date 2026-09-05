import json
from backend.gemini_client import ask_gemini


VALID_INTENTS = {
    "fishing",
    "ocean",
    "safety",
    "route",
    "general",
}

VALID_AGENTS = {
    "ocean",
    "safety",
    "route",
}


def plan_query(query: str) -> dict:
    """
    Use Gemini to understand the user's request.

    Gemini decides:
    - the main intent
    - which ORCA specialist agents may be required

    Gemini does NOT generate marine measurements or
    recommendations.
    """

    prompt = f"""
You are the AI planning module of ORCA,
a marine intelligence system.

Understand the user's request and return ONLY valid JSON.

Available specialist agents:

1. ocean
   Handles ocean/environment information such as:
   - sea surface temperature
   - chlorophyll
   - currents
   - waves
   - ocean conditions
   - fishing-potential data

2. safety
   Handles:
   - marine safety
   - weather-related risk
   - safety scores
   - risk assessment

3. route
   Handles:
   - routes
   - distance
   - travel time
   - fuel
   - navigation

Available main intents:

- fishing
- ocean
- safety
- route
- general

Rules:

1. Identify the MAIN intent of the user.

2. Identify ALL specialist agents required to answer
   the request properly.

3. For fishing recommendations, include "ocean".

4. If the user asks whether something is safe,
   include "safety".

5. If the user asks for a route, distance, travel time,
   navigation or fuel, include "route".

6. A request may require multiple agents.

7. Do NOT invent any marine measurements.

8. Do NOT calculate safety scores.

9. Do NOT calculate distances.

10. Do NOT provide the answer to the user.

11. Return ONLY JSON.

Use exactly this structure:

{{
    "intent": "fishing",
    "required_agents": ["ocean"],
    "confidence": 0.95
}}

User request:
{query}
"""

    try:
        raw = ask_gemini(prompt)

        raw = raw.strip()

        # Remove markdown code fences if Gemini adds them.
        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1)
            raw = raw.replace("```", "")
            raw = raw.strip()

        result = json.loads(raw)

        intent = result.get("intent", "general")
        agents = result.get("required_agents", [])
        confidence = result.get("confidence", 0.0)

        # Validate intent.
        if intent not in VALID_INTENTS:
            intent = "general"

        # Validate agents.
        if not isinstance(agents, list):
            agents = []

        agents = [
            agent
            for agent in agents
            if agent in VALID_AGENTS
        ]

        # Remove duplicates while preserving order.
        agents = list(dict.fromkeys(agents))

        # Validate confidence.
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        return {
            "intent": intent,
            "required_agents": agents,
            "confidence": confidence,
        }

    except Exception as e:
        # Gemini must never break ORCA.
        return {
            "intent": "general",
            "required_agents": [],
            "confidence": 0.0,
            "error": str(e),
        }