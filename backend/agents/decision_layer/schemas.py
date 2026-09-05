from pydantic import BaseModel, Field


class AgentScores(BaseModel):
    fishing_score: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=1)
    route_score: float = Field(ge=0, le=1)


class DecisionRequest(BaseModel):
    zone_id: str
    latitude: float
    longitude: float
    scores: AgentScores


class AgentOutput(BaseModel):
    zone_id: str
    score: float = Field(ge=0, le=1)
    evidence: dict = {}


class CombinedDecisionRequest(BaseModel):
    ocean: AgentOutput
    safety: AgentOutput
    route: AgentOutput
