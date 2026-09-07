"""Print a local SEA configuration for a generic STDIO MCP host or VS Code."""
import argparse
import json
from pathlib import Path
import sys


def configuration(client, python, database, registry_url=None, client_id=None,
                  client_secret_env="SEA_REGISTRY_SECRET"):
    server = {"command": str(Path(python).expanduser().resolve()),
              "args": [str(Path(__file__).resolve().parents[1] / "sea_mcp.py"),
                       "--db", str(Path(database).expanduser().resolve())]}
    if bool(registry_url) != bool(client_id):
        raise ValueError("registry URL and client ID must be supplied together")
    if registry_url:
        server["args"] += ["--registry-url", registry_url, "--client-id", client_id,
                           "--client-secret-env", client_secret_env]
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
    parser.add_argument("--registry-url")
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret-env", default="SEA_REGISTRY_SECRET",
                        help="Environment variable name only; the secret is never printed")
    args = parser.parse_args()
    print(json.dumps(configuration(args.client, args.python, args.db, args.registry_url,
                                   args.client_id, args.client_secret_env), indent=2))
