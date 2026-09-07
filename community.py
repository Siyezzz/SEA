"""SEA community packages, signed transport, local outbox, and evolvable sync policy."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import re
import secrets
import sqlite3
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from evolution import evaluate
from usage import POLICY_VERSION, status

PACKAGE_SCHEMA = "sea-wisdom/1.0"
DEFAULT_SYNC_POLICY = {"batch_size": 10, "max_attempts": 3}
COMPONENT = "community-sync-policy"
DEFAULT_REVISION = "community-sync-policy/1.0"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, name, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty text of at most {limit} characters")
    return value.strip()


def text_list(value, name, limit=20):
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{name} must be a list with at most {limit} items")
    return [text(item, name, 1000) for item in value]


PRIVATE_PATTERNS = (
    ("email", re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")),
    ("credential", re.compile(r"(?i)\b(api[_ -]?key|password|secret|token)\s*[:=]\s*\S+")),
    ("windows_path", re.compile(r"(?i)\b[A-Z]:\\(?:[^\s\\]+\\)+[^\s]+")),
    ("unix_home_path", re.compile(r"/(?:home|Users)/[^\s/]+/[^\s]+")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)
FORBIDDEN_KEYS = {"conversation", "transcript", "raw_trace", "credentials", "user_email",
                  "local_path", "project_name", "source_code", "preference"}


def privacy_findings(value, path="$", findings=None):
    """Conservative deterministic screen; a clean result is not guaranteed anonymization."""
    findings = [] if findings is None else findings
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                findings.append({"path": f"{path}.{key}", "kind": "forbidden_field"})
            privacy_findings(item, f"{path}.{key}", findings)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            privacy_findings(item, f"{path}[{index}]", findings)
    elif isinstance(value, str):
        for kind, pattern in PRIVATE_PATTERNS:
            if pattern.search(value):
                findings.append({"path": path, "kind": kind})
    return findings


def validate_package(package):
    required = {"schema", "package_id", "revision", "parent_ids", "problem", "conditions", "method",
                "counterexamples", "outcomes", "compatibility", "producer", "created_at"}
    if not isinstance(package, dict) or set(package) != required:
        raise ValueError("Wisdom package fields do not match the registered schema")
    if package["schema"] != PACKAGE_SCHEMA:
        raise ValueError("Unsupported wisdom package schema")
    text(package["package_id"], "package_id", 64)
    if not re.fullmatch(r"[0-9a-f]{64}", package["package_id"]):
        raise ValueError("package_id must be a SHA-256 digest")
    if isinstance(package["revision"], bool) or not isinstance(package["revision"], int) or package["revision"] < 1:
        raise ValueError("revision must be a positive integer")
    text_list(package["parent_ids"], "parent_ids", 8)
    text(package["problem"], "problem")
    text_list(package["conditions"], "conditions")
    text(package["method"], "method")
    text_list(package["counterexamples"], "counterexamples")
    outcomes = package["outcomes"]
    if set(outcomes) != {"successes", "failures", "mean_reward"}:
        raise ValueError("Invalid outcomes")
    if any(isinstance(outcomes[k], bool) or not isinstance(outcomes[k], int) or outcomes[k] < 0
           for k in ("successes", "failures")):
        raise ValueError("Outcome counts must be nonnegative integers")
    reward = outcomes["mean_reward"]
    if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward) or not 0 <= reward <= 1:
        raise ValueError("mean_reward must be finite and in [0,1]")
    compatibility = package["compatibility"]
    if set(compatibility) != {"models", "tools", "environments"}:
        raise ValueError("Invalid compatibility fields")
    for key in compatibility:
        text_list(compatibility[key], key)
    producer = package["producer"]
    if set(producer) != {"component", "revision", "policy_version"}:
        raise ValueError("Invalid producer fields")
    for key, value in producer.items():
        text(value, key, 200)
    text(package["created_at"], "created_at", 100)
    if privacy_findings(package):
        raise ValueError("Wisdom package failed the deterministic privacy screen")
    unsigned = dict(package)
    claimed = unsigned.pop("package_id")
    if hashlib.sha256(canonical(unsigned)).hexdigest() != claimed:
        raise ValueError("package_id does not match package content")
    return package


def build_package(memory, rewards, conditions, counterexamples, compatibility,
                  parent_ids=None, revision=1, component_revision=DEFAULT_REVISION):
    if memory["state"] != "active":
        raise ValueError("Only locally active lessons can become contribution candidates")
    rewards = list(rewards)
    if not rewards:
        raise ValueError("An active lesson needs observed feedback")
    package = {
        "schema": PACKAGE_SCHEMA,
        "revision": revision,
        "parent_ids": parent_ids or [],
        "problem": text(memory["trigger"], "problem"),
        "conditions": text_list(conditions, "conditions"),
        "method": text(memory["lesson"], "method"),
        "counterexamples": text_list(counterexamples, "counterexamples"),
        "outcomes": {"successes": sum(x >= .5 for x in rewards), "failures": sum(x < .5 for x in rewards),
                     "mean_reward": sum(rewards) / len(rewards)},
        "compatibility": {key: text_list(compatibility.get(key, []), key)
                          for key in ("models", "tools", "environments")},
        "producer": {"component": COMPONENT, "revision": component_revision,
                     "policy_version": POLICY_VERSION},
        "created_at": now(),
    }
    package["package_id"] = hashlib.sha256(canonical(package)).hexdigest()
    validate_package(package)
    return package


def init_local(kernel):
    kernel.db.executescript("""
    CREATE TABLE IF NOT EXISTS community_outbox (
      package_id TEXT PRIMARY KEY, payload TEXT, state TEXT, attempts INTEGER DEFAULT 0,
      error TEXT, remote_status TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS community_cache (
      package_id TEXT PRIMARY KEY, payload TEXT, fetched_at TEXT);
    CREATE TABLE IF NOT EXISTS component_versions (
      component TEXT, revision TEXT, parent_revision TEXT, artifact_digest TEXT,
      contract_digest TEXT, config TEXT, state TEXT, created_at TEXT,
      PRIMARY KEY(component, revision));
    """)
    row = kernel.db.execute("SELECT 1 FROM component_versions WHERE component=? AND revision=?",
                            (COMPONENT, DEFAULT_REVISION)).fetchone()
    if not row:
        kernel.db.execute("INSERT INTO component_versions VALUES(?,?,?,?,?,?,?,?)",
                          (COMPONENT, DEFAULT_REVISION, None, "builtin", "bootstrap",
                           json.dumps(DEFAULT_SYNC_POLICY), "active", now()))
        kernel.db.commit()


def sharing_choice(kernel):
    choice = status(kernel)
    if not choice["acknowledged"] or not choice["choice"]:
        raise ValueError("Current usage notice must be acknowledged before community operations")
    return choice["choice"]


def active_sync_policy(kernel):
    init_local(kernel)
    row = kernel.db.execute("SELECT revision,config FROM component_versions WHERE component=? AND state='active'",
                            (COMPONENT,)).fetchone()
    return row["revision"], json.loads(row["config"])


def queue_memory(kernel, memory_id, conditions, counterexamples, compatibility, parent_ids=None, revision=1):
    choice = sharing_choice(kernel)
    if choice["mode"] != "community-contribute":
        raise ValueError("Community contribution mode is not enabled")
    init_local(kernel)
    memory = kernel.get(memory_id)
    rewards = [row[0] for row in kernel.db.execute("SELECT reward FROM feedback WHERE memory=?", (memory_id,))]
    component_revision, _ = active_sync_policy(kernel)
    package = build_package(memory, rewards, conditions, counterexamples, compatibility,
                            parent_ids, revision, component_revision)
    stamp = now()
    with kernel.db:
        kernel.db.execute("INSERT OR IGNORE INTO community_outbox VALUES(?,?,?,0,NULL,NULL,?,?)",
                          (package["package_id"], canonical(package).decode(), "pending", stamp, stamp))
        kernel.event("community_queued", {"package_id": package["package_id"], "memory_id": memory_id})
    return {"package_id": package["package_id"], "state": "pending",
            "privacy_findings": [], "notice": "Queued locally; no upload occurs until sync is invoked."}


def sign(secret, timestamp, nonce, method, path, body):
    message = "\n".join((timestamp, nonce, method.upper(), path, hashlib.sha256(body).hexdigest())).encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class HTTPTransport:
    def __init__(self, base_url, client_id, secret, timeout=10):
        self.base_url = text(base_url, "base_url", 1000).rstrip("/")
        if not self.base_url.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            raise ValueError("Remote registries require HTTPS; HTTP is allowed only for loopback development")
        self.client_id, self.secret, self.timeout = text(client_id, "client_id", 200), text(secret, "secret", 1000), timeout

    def request(self, method, path, payload=None):
        body = b"" if payload is None else canonical(payload)
        timestamp, nonce = str(int(time.time())), secrets.token_hex(16)
        headers = {"Content-Type": "application/json", "X-SEA-Client": self.client_id,
                   "X-SEA-Timestamp": timestamp, "X-SEA-Nonce": nonce,
                   "X-SEA-Signature": sign(self.secret, timestamp, nonce, method, path, body),
                   "X-SEA-Policy-Version": POLICY_VERSION}
        request = Request(self.base_url + path, data=body if method != "GET" else None,
                          headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())


def sync_pending(kernel, transport):
    choice = sharing_choice(kernel)
    if choice["mode"] != "community-contribute":
        raise ValueError("Community contribution mode is not enabled")
    revision, policy = active_sync_policy(kernel)
    rows = kernel.db.execute("SELECT * FROM community_outbox WHERE state IN ('pending','retry') "
                             "AND attempts<? ORDER BY created_at LIMIT ?",
                             (policy["max_attempts"], policy["batch_size"])).fetchall()
    results = []
    for row in rows:
        payload = json.loads(row["payload"])
        code, response = transport.request("POST", "/v1/packages", payload)
        state = "sent" if code in (200, 201) else ("retry" if code >= 500 else "rejected")
        error = None if state == "sent" else response.get("error", f"HTTP {code}")
        with kernel.db:
            kernel.db.execute("UPDATE community_outbox SET state=?,attempts=attempts+1,error=?,remote_status=?,updated_at=? "
                              "WHERE package_id=?", (state, error, str(code), now(), row["package_id"]))
            kernel.event("community_sync", {"package_id": row["package_id"], "state": state,
                                             "component_revision": revision})
        results.append({"package_id": row["package_id"], "state": state, "status": code})
    return {"component_revision": revision, "results": results}


def evolve_sync_policy(kernel, report, revision, parent_revision, artifact_digest, config):
    """Activate bounded data configuration only after SEA's fixed independent comparison gate."""
    init_local(kernel)
    if set(config) != {"batch_size", "max_attempts"}:
        raise ValueError("Sync policy config has unsupported fields")
    for key, upper in (("batch_size", 50), ("max_attempts", 10)):
        if isinstance(config[key], bool) or not isinstance(config[key], int) or not 1 <= config[key] <= upper:
            raise ValueError(f"{key} is outside its bounded range")
    current_revision, _ = active_sync_policy(kernel)
    if parent_revision != current_revision:
        raise ValueError("Candidate parent must be the active sync policy")
    result = evaluate(report)
    matches = [item for item in result["decisions"] if item["component"] == COMPONENT and item["revision"] == revision]
    if len(matches) != 1 or matches[0]["decision"] != "eligible":
        raise ValueError("Candidate sync policy is not eligible under the supplied comparison")
    contract_digest = result["contract_sha256"]
    with kernel.db:
        kernel.db.execute("UPDATE component_versions SET state='predecessor' WHERE component=? AND state='active'",
                          (COMPONENT,))
        kernel.db.execute("INSERT INTO component_versions VALUES(?,?,?,?,?,?,?,?)",
                          (COMPONENT, revision, parent_revision, text(artifact_digest, "artifact_digest", 200),
                           contract_digest, json.dumps(config), "active", now()))
        kernel.event("component_activated", {"component": COMPONENT, "revision": revision,
                                              "parent": parent_revision, "contract": contract_digest})
    return {"component": COMPONENT, "active_revision": revision, "predecessor": parent_revision,
            "config": config, "evaluation": matches[0], "contract_sha256": contract_digest}


def search_path(query, limit=5):
    return "/v1/search?" + urlencode({"q": query, "limit": limit})
