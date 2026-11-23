"""Shared Composio MCP + Firecrawl helpers for the SaaS integration research project."""
import asyncio
import json
import os
import re
from typing import Any

import httpx2
from dotenv import load_dotenv
from composio import Composio
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

USER_ID = os.getenv("COMPOSIO_USER_ID", "research_agent_user")
SEARCH_USE_CASE = (
    "Search the public internet for official developer documentation, API references, "
    "authentication requirements, developer access restrictions, API capabilities, "
    "and existing Model Context Protocol servers for SaaS applications."
)

def _json_from_blocks(result: Any) -> Any:
    """Decode MCP text blocks where possible; preserve plain text otherwise."""
    decoded = []
    for block in getattr(result, "content", []) or []:
        value = getattr(block, "text", None)
        if value is None:
            continue
        try:
            decoded.append(json.loads(value))
        except (json.JSONDecodeError, TypeError):
            decoded.append(value)
    if len(decoded) == 1:
        return decoded[0]
    return decoded

def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)

def extract_urls(value: Any) -> list[str]:
    text = _as_text(value)
    found = re.findall(r'https?://[^\s<>"\'\]\[)]+', text, flags=re.I)
    cleaned = []
    for url in found:
        url = url.rstrip(".,;:")
        if url not in cleaned:
            cleaned.append(url)
    return cleaned

def compact_text(value: Any, limit: int = 10000) -> str:
    text = _as_text(value)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]

def _find_session_id(payload: Any) -> str | None:
    if isinstance(payload, dict):
        session = payload.get("session")
        if isinstance(session, dict) and session.get("id"):
            return str(session["id"])
        for value in payload.values():
            found = _find_session_id(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_session_id(value)
            if found:
                return found
    return None

class ResearchClient:
    """Owns one MCP session and executes discovered Firecrawl app tools."""
    def __init__(self):
        self.composio = Composio()
        self.session = None
        self.http_client = None
        self.transport_cm = None
        self.client_cm = None
        self.client = None
        self.session_id = None

    async def __aenter__(self):
        from contextlib import AsyncExitStack

        self.stack = AsyncExitStack()
        await self.stack.__aenter__()

        self.session = self.composio.sessions.create(user_id=USER_ID, mcp=True)
        self.http_client = await self.stack.enter_async_context(
            httpx2.AsyncClient(
                headers=self.session.mcp.headers,
                timeout=httpx2.Timeout(30, read=300)
            )
        )
        transport = streamable_http_client(
            self.session.mcp.url, http_client=self.http_client
        )
        # Client owns the transport context; AsyncExitStack closes both safely.
        self.client = await self.stack.enter_async_context(Client(transport))

        discovery = await self.client.call_tool(
            "COMPOSIO_SEARCH_TOOLS",
            arguments={
                "queries": [{"use_case": SEARCH_USE_CASE}],
                "session": {"generate_id": True},
                "search_strategy": "tool_search"
            }
        )
        discovery_data = _json_from_blocks(discovery)
        self.session_id = _find_session_id(discovery_data)
        if not self.session_id:
            message = (
                "Composio tool discovery did not return a session ID. "
                f"Discovery response: {compact_text(discovery_data, 2000)}"
            )
            await self.stack.__aexit__(None, None, None)
            self.stack = None
            raise RuntimeError(message)

        # Do not fail based on a brittle text search through nested MCP results.
        # The discovery response can be wrapped differently across SDK versions.
        # Actual tool execution below will return the authoritative error if a slug
        # is unavailable or the connection is inactive.
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if getattr(self, "stack", None):
            await self.stack.__aexit__(exc_type, exc, tb)

    async def execute(self, tool_slug: str, arguments: dict) -> Any:
        if not self.client or not self.session_id:
            raise RuntimeError("ResearchClient is not connected.")
        result = await self.client.call_tool(
            "COMPOSIO_MULTI_EXECUTE_TOOL",
            arguments={
                "tools": [{"tool_slug": tool_slug, "arguments": arguments}],
                "sync_response_to_workbench": False,
                "thought": f"Use {tool_slug} to collect official product documentation evidence.",
                "current_step": "RESEARCHING_APPS",
                "current_step_metric": "Collecting official evidence",
                "session_id": self.session_id
            }
        )
        decoded = _json_from_blocks(result)
        # Surface MCP-level error blocks rather than silently treating them as data.
        if getattr(result, "isError", False):
            raise RuntimeError(compact_text(decoded, 3000))
        return decoded

    async def search(self, query: str, limit: int = 5) -> Any:
        return await self.execute(
            "FIRECRAWL_SEARCH",
            {"q": query, "limit": limit, "formats": ["markdown"]}
        )

    async def scrape(self, url: str) -> Any:
        return await self.execute(
            "FIRECRAWL_SCRAPE",
            {"url": url, "formats": ["markdown"], "onlyMainContent": True}
        )

def classify_research(app: str, category: str, hint: str, search_data: list, scraped: list) -> dict:
    """Conservative evidence extraction. Unknowns remain explicitly unknown."""
    corpus = "\n".join(
        [_as_text(x) for x in search_data] +
        [_as_text(x.get("content", "")) for x in scraped]
    )
    low = corpus.lower()

    auth_hits = []
    for label, patterns in {
        "OAuth 2.0": [r'oauth\s*2', r'oauth 2\.0'],
        "API key": [r'api key', r'api-key', r'x-api-key'],
        "Bearer token": [r'bearer token', r'authorization:\s*bearer'],
        "Basic authentication": [r'basic authentication', r'basic auth'],
        "JWT": [r'\bjwt\b', r'json web token'],
    }.items():
        if any(re.search(p, low) for p in patterns):
            auth_hits.append(label)
    authentication = ", ".join(auth_hits) if auth_hits else "Not established from collected evidence"

    if any(x in low for x in ["developer portal", "create an app", "self-service", "self serve", "sign up for an api key"]):
        developer_access = "Likely self-serve; confirm account/plan requirements"
    elif any(x in low for x in ["contact sales", "request access", "partner program", "private beta", "approval required"]):
        developer_access = "Gated or approval-based access indicated"
    else:
        developer_access = "Not established from collected evidence"

    if any(x in low for x in ["graphql", "graphql api"]):
        api_type = "REST and/or GraphQL (verify exact supported interfaces)"
    elif any(x in low for x in ["rest api", "restful api", "http api"]):
        api_type = "REST"
    elif any(x in low for x in ["webhook", "webhooks"]):
        api_type = "Webhooks mentioned; API type needs confirmation"
    else:
        api_type = "Not established from collected evidence"

    mcp_present = bool(re.search(r'\bmodel context protocol\b|\bmcp server\b|\bmcp integration\b', low))
    existing_mcp = "Evidence found; inspect cited source" if mcp_present else "No MCP evidence found in this search (not proof none exists)"

    api_signals = sum(bool(re.search(p, low)) for p in [
        r'api reference', r'api endpoint', r'api documentation', r'sdk',
        r'webhook', r'pagination', r'rate limit', r'oauth'
    ])
    if api_signals >= 5:
        breadth = "Broad API surface indicated"
    elif api_signals >= 2:
        breadth = "Some API capabilities indicated"
    elif api_signals >= 1:
        breadth = "Limited API evidence collected"
    else:
        breadth = "Insufficient evidence"

    description = ""
    for item in scraped:
        content = str(item.get("content", ""))
        if content:
            description = content[:420].strip()
            break
    if not description:
        description = f"{app} is listed in the {category} category; product description needs source verification."

    blockers = []
    if authentication == "Not established from collected evidence":
        blockers.append("Authentication method not confirmed")
    if developer_access == "Not established from collected evidence":
        blockers.append("Developer access model not confirmed")
    if api_type == "Not established from collected evidence":
        blockers.append("API type not confirmed")
    if not scraped:
        blockers.append("No official page was successfully scraped")
    if not mcp_present:
        blockers.append("No existing MCP server evidence found; absence not verified")

    if not scraped or len(blockers) >= 3:
        buildability = "Insufficient evidence"
    elif authentication != "Not established from collected evidence" and api_type != "Not established from collected evidence":
        buildability = "Potentially buildable; validate endpoints, scopes and terms"
    else:
        buildability = "Needs further investigation"

    evidence_urls = []
    for item in scraped:
        if item.get("url") and item["url"] not in evidence_urls:
            evidence_urls.append(item["url"])

    return {
        "id": None,
        "app": app,
        "category": category,
        "domain": hint,
        "description": description,
        "authentication": authentication,
        "developer_access": developer_access,
        "api_type": api_type,
        "api_breadth": breadth,
        "existing_mcp": existing_mcp,
        "buildability": buildability,
        "blockers": blockers,
        "evidence_urls": evidence_urls,
        "status": "needs_human_review",
        "research_notes": "Rule-based extraction from Firecrawl search/scrape output. Verify every conclusion against official documentation."
    }
