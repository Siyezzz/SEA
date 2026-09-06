# SEA in other MCP clients

SEA's server speaks standard MCP over local STDIO. The Codex plugin bundles a host-specific skill and manifest; `sea_mcp.py` itself has no Codex dependency. A host that can launch a Python subprocess and call MCP tools can connect. A remote-HTTP-only client cannot use this local endpoint directly; SEA does not currently provide an authenticated HTTP deployment.

Use Python 3.10+ with `requirements-mcp.txt` installed. Run `scripts/mcp_config.py` with that interpreter to generate absolute paths for the current machine. `--client generic` emits a `mcpServers` object; `--client vscode` emits a `servers` object with `type: stdio`. Merge only the SEA entry into the host's existing configuration; do not replace unrelated servers.

Generic shape (replace paths with real absolute paths):

```json
{
  "mcpServers": {
    "sea": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/SEA/sea_mcp.py", "--db", "/absolute/private/path/memory.sqlite3"]
    }
  }
}
```

VS Code uses a different wrapper:

```json
{
  "servers": {
    "sea": {
      "type": "stdio",
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/SEA/sea_mcp.py", "--db", "/absolute/private/path/memory.sqlite3"]
    }
  }
}
```

On Windows, the interpreter is typically `.venv/Scripts/python.exe`; the generator handles JSON escaping. Paths belong to the machine running the MCP host. Do not distribute your generated personal configuration as a portable plugin.

After connection, ask the host to show SEA's usage notice and record your explicit mode choice. Then ask it to retrieve relevant experience and record evidence while doing your task. The Codex skill is not automatically installed in other products; adapt its workflow to the host's supported instructions mechanism. MCP connectivity alone does not create a perpetual learning loop.

The host chooses its own model. Several hosts owned by the same user can point to one local database; different owners should use separate databases. SQLite is local storage, not a distributed synchronization service. Remote community exchange is a separate planned service.

Protocol initialization, discovery, tool calls, and restart persistence are tested with the official Python MCP client. The VS Code format is documented but has not been interactively tested in VS Code on this machine. See [VS Code MCP servers](https://code.visualstudio.com/docs/agent-customization/mcp-servers) and the [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/index).
