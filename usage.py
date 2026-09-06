"""Versioned, local acknowledgement for the standard MCP entry point."""
from datetime import datetime, timezone

POLICY_VERSION = "2026-09-06.1"
MODES = ("community-contribute", "community-read", "local-only")
NOTICE = {
    "version": POLICY_VERSION,
    "recommended_mode": "community-contribute",
    "acknowledgement_required": True,
    "summary": "Learn locally and, when a community service is available and authorized, give back reusable non-private experience.",
    "eligible_data": ["Reviewed general methods", "Synthetic examples", "Non-private evaluation summaries and counterexamples"],
    "excluded_data": ["Raw conversations", "Private files or source code", "Credentials", "Personal identifiers",
                      "Local preferences", "Private paths, project names, and raw execution traces"],
    "controls": "The user may choose or change mode. A default selection is not acknowledgement. Downloads are not consent.",
    "local_only": "Keeps model capabilities and local experience. No community exchange; learning does not start from zero.",
    "host_data": "Memory returned to the host is handled under that host/model provider's data settings.",
    "service_status": "Not connected: this release has no community upload, search, or telemetry client.",
    "future_activation": "Disclose the actual recipient, data fields, retention, and reuse terms and obtain acknowledgement before enabling a future service.",
    "privacy_limit": "Automated sensitive-data detection cannot guarantee anonymization. Review generalizations before contribution.",
}


def status(kernel):
    kernel.db.execute("CREATE TABLE IF NOT EXISTS usage_policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                      "version TEXT, mode TEXT, source TEXT, acknowledged_at TEXT)")
    row = kernel.db.execute("SELECT version,mode,source,acknowledged_at FROM usage_policy WHERE singleton=1").fetchone()
    current = dict(row) if row else None
    return {"notice": NOTICE, "choice": current,
            "acknowledged": bool(current and current["version"] == POLICY_VERSION),
            "sharing_active": False}


def acknowledge(kernel, version, mode, source, user_acknowledged):
    if user_acknowledged is not True:
        raise ValueError("An explicit user acknowledgement is required; do not infer it from installation")
    if version != POLICY_VERSION or mode not in MODES or not source.strip():
        raise ValueError("Use the current notice version, a supported mode, and the actual user acknowledgement source")
    status(kernel)
    record = (version, mode, source, datetime.now(timezone.utc).isoformat())
    with kernel.db:
        kernel.db.execute("INSERT INTO usage_policy VALUES(1,?,?,?,?) ON CONFLICT(singleton) "
                          "DO UPDATE SET version=excluded.version,mode=excluded.mode,source=excluded.source,"
                          "acknowledged_at=excluded.acknowledged_at", record)
        kernel.event("usage_acknowledged", dict(zip(("version", "mode", "source", "acknowledged_at"), record)))
    return status(kernel)


def require_acknowledgement(kernel):
    if not status(kernel)["acknowledged"]:
        raise ValueError("SEA first use: call get_usage_status, show the notice and recommended sharing mode, "
                         "then acknowledge_usage only after the user's explicit choice. No data has been uploaded.")
