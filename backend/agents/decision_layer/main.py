from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.agents.decision_layer.schemas import DecisionRequest, CombinedDecisionRequest
from backend.agents.decision_layer.scoring import calculate_final_score
from backend.agents.decision_layer.constraints import apply_constraints

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

app = FastAPI(
    title="ORCA Decision Layer",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:8080",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_why(fishing_score, risk_score, safety_score, route_score, decision):
    reasons = []

    if fishing_score >= 0.7:
        reasons.append("high fishing potential")
    elif fishing_score >= 0.5:
        reasons.append("moderate fishing potential")
    else:
        reasons.append("low fishing potential")

    if safety_score >= 0.7:
        reasons.append("good safety conditions")
    elif safety_score >= 0.5:
        reasons.append("moderate safety conditions")
    else:
        reasons.append("high safety risk")

    if route_score >= 0.8:
        reasons.append("very good route accessibility")
    elif route_score >= 0.5:
        reasons.append("moderate route accessibility")
    else:
        reasons.append("difficult route")

    return (
        f"Zone selected as {decision} because it has "
        + ", ".join(reasons)
        + f". Final decision score is {round((0.40*fishing_score + 0.35*safety_score + 0.25*route_score), 4)}."
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def home():
    return {
        "system": "ORCA Decision Layer",
        "status": "running"
    }


@app.post("/decision")
def make_decision(request: DecisionRequest):

    safety_score = 1 - request.scores.risk_score

    final_score = calculate_final_score(
        request.scores.fishing_score,
        request.scores.risk_score,
        request.scores.route_score
    )

    decision = apply_constraints(
        safety_score,
        final_score
    )

    why = generate_why(
        request.scores.fishing_score,
        request.scores.risk_score,
        safety_score,
        request.scores.route_score,
        decision
    )

    return {
        "zone_id": request.zone_id,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "fishing_score": request.scores.fishing_score,
        "risk_score": request.scores.risk_score,
        "safety_score": round(safety_score, 4),
        "route_score": request.scores.route_score,
        "final_score": final_score,
        "decision": decision,
        "why": why
    }


@app.post("/decision/combined")
def combined_decision(request: CombinedDecisionRequest):

    fishing_score = request.ocean.score
    risk_score = request.safety.score
    route_score = request.route.score

    safety_score = 1 - risk_score

    final_score = calculate_final_score(
        fishing_score,
        risk_score,
        route_score
    )

    decision = apply_constraints(
        safety_score,
        final_score
    )

    why = generate_why(
        fishing_score,
        risk_score,
        safety_score,
        route_score,
        decision
    )

    return {
        "recommended_zone": request.ocean.zone_id,
        "decision": decision,
        "final_score": final_score,
        "statistics": {
            "fishing_score": fishing_score,
            "risk_score": risk_score,
            "safety_score": round(safety_score, 4),
            "route_score": route_score
        },
        "evidence": {
            "fishing": request.ocean.evidence,
            "safety": request.safety.evidence,
            "route": request.route.evidence
        },
        "why": why
    }