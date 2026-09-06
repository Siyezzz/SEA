"""Print a local SEA configuration for a generic STDIO MCP host or VS Code."""
import argparse
import json
from pathlib import Path
import sys


def configuration(client, python, database):
    server = {"command": str(Path(python).expanduser().resolve()),
              "args": [str(Path(__file__).resolve().parents[1] / "sea_mcp.py"),
                       "--db", str(Path(database).expanduser().resolve())]}
    if client == "vscode":
        server["type"] = "stdio"
        return {"servers": {"sea": server}}
    if client == "generic":
        return {"mcpServers": {"sea": server}}
    raise ValueError("Unsupported client format")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("generic", "vscode"), default="generic")
    parser.add_argument("--python", default=sys.executable, help="Interpreter with requirements-mcp.txt installed")
    parser.add_argument("--db", type=Path, default=Path.home() / ".sea" / "memory.sqlite3")
    args = parser.parse_args()
    print(json.dumps(configuration(args.client, args.python, args.db), indent=2))
