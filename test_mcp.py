
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

try:
    composio = Composio()

    session = composio.sessions.create(
        user_id="research_agent_user",
        mcp=True
    )

    print("SUCCESS: MCP session created!")
    print("Session ID:", session.session_id)
    print("MCP URL available:", bool(session.mcp.url))
    print("MCP headers available:", bool(session.mcp.headers))

except Exception as e:
    print("MCP setup failed.")
    print(type(e).__name__, str(e))
