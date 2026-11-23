
import asyncio
import httpx2
from dotenv import load_dotenv
from composio import Composio
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

async def main():
    composio = Composio()

    session = composio.sessions.create(
        user_id="research_agent_user",
        mcp=True
    )

    async with httpx2.AsyncClient(
        headers=session.mcp.headers,
        timeout=httpx2.Timeout(30, read=300)
    ) as http_client:

        transport = streamable_http_client(
            session.mcp.url,
            http_client=http_client
        )

        async with Client(transport) as client:
            result = await client.list_tools()

            for tool in result.tools:
                if tool.name in (
                    "COMPOSIO_MULTI_EXECUTE_TOOL",
                    "COMPOSIO_GET_TOOL_SCHEMAS",
                    "COMPOSIO_REMOTE_WORKBENCH"
                ):
                    print("\n" + "=" * 60)
                    print("TOOL:", tool.name)
                    print("INPUT SCHEMA:")
                    print(tool.input_schema)
                    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
