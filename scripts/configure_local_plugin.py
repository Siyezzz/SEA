"""Populate an existing SEA plugin scaffold with a tested local server snapshot.

Run with the MCP-enabled Python environment. Does not edit marketplace or Codex settings.
The generated config is machine-local: regenerate it on each machine before installation.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys


def configure(plugin: Path, database: Path, registry_url=None, client_id=None, client_secret_env="SEA_REGISTRY_SECRET"):
    root = Path(__file__).resolve().parents[1]
    plugin = plugin.expanduser().resolve()
    manifest_path = plugin / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if plugin.name != "sea" or manifest.get("name") != "sea":
        raise ValueError("Expected an existing SEA scaffold")
    import mcp  # Fail before writing if this interpreter cannot run the server.
    runtime = plugin / "runtime"
    runtime.mkdir(exist_ok=True)
    for name in ("kernel.py", "evolution.py", "sea_mcp.py", "usage.py", "community.py", "requirements-mcp.txt", "LICENSE"):
        shutil.copy2(root / name, runtime / name)
    skill = plugin / "skills" / "experience-core"
    shutil.copytree(root / "skills" / "experience-core", skill, dirs_exist_ok=True)
    # Keep the packaged comparison reference synchronized with its canonical source.
    shutil.copy2(root / "docs" / "algorithms.md", skill / "references" / "algorithms.md")
    shutil.copytree(root / "assets", plugin / "assets", dirs_exist_ok=True)
    if bool(registry_url) != bool(client_id):
        raise ValueError("registry URL and client ID must be supplied together")
    manifest.update(description="Local experience memory with optional signed community exchange for Codex chat.",
                    author={"name": "Li Siye"}, repository="https://github.com/Siyezzz/SEA",
                    license="MIT", skills="./skills/", mcpServers="./.mcp.json")
    manifest["interface"].update(displayName="SEA", shortDescription="Learn from tasks through chat.",
        longDescription="Local preferences, project experience, evidence-based candidate comparison, and optional signed community exchange.",
        developerName="Li Siye", defaultPrompt=["Use SEA for this task.", "What has SEA learned from this project?"],
        brandColor="#238BB4", composerIcon="./assets/sea-icon.png", logo="./assets/sea-icon.png",
        logoDark="./assets/sea-icon.png")
    server_args = [str(runtime / "sea_mcp.py"), "--db", str(database.expanduser().resolve())]
    if registry_url:
        server_args += ["--registry-url", registry_url, "--client-id", client_id,
                        "--client-secret-env", client_secret_env]
    config = {"mcpServers": {"sea": {"command": str(Path(sys.executable).resolve()), "args": server_args}}}
    for path, value in ((manifest_path, manifest), (plugin / ".mcp.json", config)):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(f"Configured local SEA plugin: {plugin}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path, default=Path.home() / "plugins" / "sea")
    parser.add_argument("--db", type=Path, default=Path.home() / ".sea" / "memory.sqlite3")
    parser.add_argument("--registry-url")
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret-env", default="SEA_REGISTRY_SECRET",
                        help="Environment variable name only; the secret is never written to plugin files")
    args = parser.parse_args()
    configure(args.plugin, args.db, args.registry_url, args.client_id, args.client_secret_env)
