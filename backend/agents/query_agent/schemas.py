from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    latitude: float | None = None
    longitude: float | None = None
    conversation_id: str | None = None


class ParsedQuery(BaseModel):
    query: str
    intents: list[str]
    latitude: float | None = None
    longitude: float | None = None
    datetime: str | None = None
    origin: str | None = None
    required_agents: list[str]
