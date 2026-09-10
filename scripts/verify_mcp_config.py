"""Verify a generated SEA MCP configuration without exposing client secrets."""
import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def decode(result):
    if result.isError:
        raise RuntimeError(result.content[0].text)
    return json.loads(result.content[0].text)


async def verify(config_path, query):
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    entry = config["mcpServers"]["sea"]
    params = StdioServerParameters(command=entry["command"], args=entry["args"])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            tools = await session.list_tools()
            usage = decode(await session.call_tool("get_usage_status", {}))
            search = decode(await session.call_tool("search_community", {"query": query, "limit": 3}))
            return {"tool_count": len(tools.tools), "acknowledged": usage["acknowledged"],
                    "sharing_active": usage["sharing_active"], "registry": usage["registry"],
                    "search_result_count": len(search["items"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--query", default="synthetic connectivity")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(verify(args.config, args.query)), indent=2))
