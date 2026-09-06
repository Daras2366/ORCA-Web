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
    Use Gemini as the primary semantic planner for ORCA.

    Gemini determines:
    - user's language
    - main intent
    - required specialist agents
    - relevant entities
    - requested operations

    Gemini does NOT answer the user here.
    """

    prompt = f"""
You are the AI planning and routing module of ORCA,
a marine intelligence system.

Your job is to understand the user's request and create
a structured execution plan for ORCA's specialist agents.

You MUST NOT answer the user.

You MUST return ONLY valid JSON.

==================================================
SUPPORTED SPECIALIST AGENTS
==================================================

1. ocean

Use the ocean agent for:
- fishing potential
- fishing zones
- sea surface temperature
- SST
- chlorophyll
- ocean conditions
- currents
- waves when used as ocean information
- marine environmental conditions

2. safety

Use the safety agent for:
- marine safety
- weather-related risk
- dangerous conditions
- wind risk
- wave risk
- storm risk
- cyclone risk
- rainfall risk
- safety assessment
- whether it is safe to travel or fish

3. route

Use the route agent for:
- route planning
- distance
- travel time
- fuel
- navigation
- route accessibility
- getting from the user's location to a fishing zone

==================================================
INTENTS
==================================================

Use exactly one main intent:

- fishing
- ocean
- safety
- route
- general

==================================================
LANGUAGE
==================================================

Detect the language of the user's query.

Return a BCP-47 language code when possible.

Examples:

English -> "en"
Hindi -> "hi"
Marathi -> "mr"
Tamil -> "ta"
Telugu -> "te"
Bengali -> "bn"
Malayalam -> "ml"
Kannada -> "kn"
Gujarati -> "gu"
Punjabi -> "pa"

If uncertain, use "en".

The language is important because ORCA's final response
should eventually be generated in the user's language.

==================================================
AGENT SELECTION RULES
==================================================

Select ALL specialist agents required to answer the request.

Examples:

"Where should I go fishing?"
-> ocean

"Is it safe to go fishing?"
-> safety

"How far is the fishing zone?"
-> route

"Give me a fishing location, tell me if it is safe,
and give me the best route."
-> ocean + safety + route

"Where should I fish and how do I get there?"
-> ocean + route

"Find a fishing spot and check whether it is safe."
-> ocean + safety

A fishing recommendation normally requires "ocean".

If the user asks whether something is safe,
include "safety".

If the user asks for route, distance, travel time,
navigation, or fuel, include "route".

A request may require multiple agents.

==================================================
ENTITY EXTRACTION
==================================================

Extract useful information from the query when present.

Possible entities:

- location
- latitude
- longitude
- zone_id
- comparison_zone
- date
- time
- destination

Do NOT invent values.

If a value is not present, use null.

==================================================
REQUIREMENTS
==================================================

Determine what the user is asking ORCA to do.

Return boolean fields:

find_best_zone
check_safety
calculate_route
compare_zones
provide_ocean_conditions

Only set a field to true when the user actually requests
that operation or it is clearly necessary for the requested
intent.

==================================================
IMPORTANT
==================================================

Do NOT:

- answer the user's question
- invent measurements
- invent coordinates
- invent zone IDs
- calculate safety scores
- calculate distances
- fabricate weather
- fabricate ocean conditions
- make the final recommendation

The specialist agents and Decision Layer will do those jobs.

==================================================
OUTPUT FORMAT
==================================================

Return exactly this JSON structure:

{{
    "language": "en",
    "intent": "fishing",
    "required_agents": [
        "ocean",
        "safety",
        "route"
    ],
    "entities": {{
        "location": null,
        "latitude": null,
        "longitude": null,
        "zone_id": null,
        "comparison_zone": null,
        "date": null,
        "time": null,
        "destination": null
    }},
    "requirements": {{
        "find_best_zone": true,
        "check_safety": true,
        "calculate_route": true,
        "compare_zones": false,
        "provide_ocean_conditions": true
    }},
    "confidence": 0.95
}}

==================================================
USER QUERY
==================================================

{query}
"""

    try:
        raw = ask_gemini(prompt)

        raw = raw.strip()

        # Remove Markdown code fences if Gemini adds them.
        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1)
            raw = raw.replace("```", "")
            raw = raw.strip()

        result = json.loads(raw)

        # --------------------------------------------------
        # Validate language
        # --------------------------------------------------

        language = result.get("language", "en")

        if not isinstance(language, str) or not language:
            language = "en"

        # --------------------------------------------------
        # Validate intent
        # --------------------------------------------------

        intent = result.get("intent", "general")

        if intent not in VALID_INTENTS:
            intent = "general"

        # --------------------------------------------------
        # Validate agents
        # --------------------------------------------------

        agents = result.get("required_agents", [])

        if not isinstance(agents, list):
            agents = []

        agents = [
            agent
            for agent in agents
            if agent in VALID_AGENTS
        ]

        # Remove duplicates while preserving order.
        agents = list(dict.fromkeys(agents))

        # --------------------------------------------------
        # Validate entities
        # --------------------------------------------------

        entities = result.get("entities", {})

        if not isinstance(entities, dict):
            entities = {}

        normalized_entities = {
            "location": entities.get("location"),
            "latitude": entities.get("latitude"),
            "longitude": entities.get("longitude"),
            "zone_id": entities.get("zone_id"),
            "comparison_zone": entities.get(
                "comparison_zone"
            ),
            "date": entities.get("date"),
            "time": entities.get("time"),
            "destination": entities.get("destination"),
        }

        # --------------------------------------------------
        # Validate requirements
        # --------------------------------------------------

        requirements = result.get(
            "requirements",
            {}
        )

        if not isinstance(requirements, dict):
            requirements = {}

        normalized_requirements = {
            "find_best_zone": bool(
                requirements.get(
                    "find_best_zone",
                    False
                )
            ),
            "check_safety": bool(
                requirements.get(
                    "check_safety",
                    False
                )
            ),
            "calculate_route": bool(
                requirements.get(
                    "calculate_route",
                    False
                )
            ),
            "compare_zones": bool(
                requirements.get(
                    "compare_zones",
                    False
                )
            ),
            "provide_ocean_conditions": bool(
                requirements.get(
                    "provide_ocean_conditions",
                    False
                )
            ),
        }

        # --------------------------------------------------
        # Validate confidence
        # --------------------------------------------------

        confidence = result.get(
            "confidence",
            0.0
        )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(
            0.0,
            min(1.0, confidence)
        )

        return {
            "language": language,
            "intent": intent,
            "required_agents": agents,
            "entities": normalized_entities,
            "requirements": normalized_requirements,
            "confidence": confidence,
        }

    except Exception as e:
        # Gemini failure should not crash the entire
        # Query Agent. The deterministic parser can act
        # as a fallback.
        return {
            "language": "en",
            "intent": "general",
            "required_agents": [],
            "entities": {},
            "requirements": {},
            "confidence": 0.0,
            "error": str(e),
        }