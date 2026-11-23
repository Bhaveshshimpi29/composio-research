"""The record schema. Fixed values wherever possible; 'unknown' is always a legal answer."""
from typing import Literal
from pydantic import BaseModel, Field

AUTH = ["oauth2", "api_key", "basic", "bearer_token", "other", "none_found", "unknown"]
ACCESS = ["self_serve_free", "free_trial", "paid_plan", "admin_approval", "partner_or_sales", "unknown"]
API_TYPE = ["rest", "graphql", "soap", "sdk_only", "none_public", "unknown"]
BREADTH = ["small", "medium", "large", "unknown"]
MCP = ["official", "community", "none_found", "unknown"]
BUILDABLE = ["yes", "partial", "no", "unknown"]
BLOCKER = ["none", "no_public_api", "paid_plan", "partner_gate", "admin_approval",
           "auth_complexity", "docs_missing", "other", "unknown"]
CONF = ["high", "medium", "low"]

# fields scored against the gold sample
SCORED = ["auth_methods", "access", "main_blocker", "existing_mcp", "buildable_today"]
# fields that must carry a verbatim quote
EVIDENCED = ["auth_methods", "access", "api_type", "api_breadth", "existing_mcp", "buildable_today", "main_blocker"]
# the risky ones the second-opinion agent re-answers
RISKY = ["access", "auth_methods", "main_blocker"]
UNKNOWN_VALUE = {"auth_methods": ["unknown"], "api_type": ["unknown"]}   # others: "unknown"
GATED_ACCESS = {"admin_approval", "partner_or_sales"}

class Evidence(BaseModel):
    field: str
    url: str
    quote: str = Field(description="exact sentence copied word for word from the page")

class Extraction(BaseModel):
    """What the extraction LLM must return (via forced tool call)."""
    category: str = Field(description="short label, e.g. CRM, payments, dev tools")
    one_liner: str
    auth_methods: list[Literal[tuple(AUTH)]]
    access: Literal[tuple(ACCESS)]
    api_type: list[Literal[tuple(API_TYPE)]]
    api_breadth: Literal[tuple(BREADTH)]
    existing_mcp: Literal[tuple(MCP)]
    existing_mcp_url: str = ""
    buildable_today: Literal[tuple(BUILDABLE)]
    main_blocker: Literal[tuple(BLOCKER)]
    evidence: list[Evidence]
    confidence: Literal[tuple(CONF)]

class SecondOpinion(BaseModel):
    auth_methods: list[Literal[tuple(AUTH)]]
    access: Literal[tuple(ACCESS)]
    main_blocker: Literal[tuple(BLOCKER)]
    evidence: list[Evidence]
