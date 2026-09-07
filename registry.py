"""Reference SEA community registry with signed requests and SQLite persistence."""
import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import sqlite3
import time
from urllib.parse import parse_qs

from community import canonical, now, sign, validate_package
from kernel import terms
from usage import POLICY_VERSION


class Registry:
    def __init__(self, path=":memory:", clock=time.time):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.clock = clock
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
          id TEXT PRIMARY KEY, secret TEXT, policy_version TEXT, can_contribute INTEGER);
        CREATE TABLE IF NOT EXISTS nonces (
          client TEXT, nonce TEXT, used_at INTEGER, PRIMARY KEY(client,nonce));
        CREATE TABLE IF NOT EXISTS packages (
          id TEXT PRIMARY KEY, revision INTEGER, parent_ids TEXT, body TEXT, author TEXT,
          state TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS community_feedback (
          package TEXT, client TEXT, task TEXT, reward REAL, evidence_digest TEXT, created_at TEXT,
          PRIMARY KEY(package,client,task));
        """)

    def register_client(self, client_id, secret, policy_version=POLICY_VERSION, can_contribute=True):
        if not client_id.strip() or len(secret) < 16:
            raise ValueError("Client ID and at least 16 secret characters are required")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO clients VALUES(?,?,?,?)",
                            (client_id, secret, policy_version, int(can_contribute)))

    def authenticate(self, method, path, body, headers, contribution=False):
        normalized = {key.lower(): value for key, value in headers.items()}
        client = normalized.get("x-sea-client", "")
        row = self.db.execute("SELECT * FROM clients WHERE id=?", (client,)).fetchone()
        if not row or normalized.get("x-sea-policy-version") != row["policy_version"]:
            raise PermissionError("Unknown client or unaccepted service policy")
        if contribution and not row["can_contribute"]:
            raise PermissionError("Client is not authorized to contribute")
        timestamp, nonce = normalized.get("x-sea-timestamp", ""), normalized.get("x-sea-nonce", "")
        try:
            numeric_time = int(timestamp)
        except ValueError as error:
            raise PermissionError("Invalid timestamp") from error
        if abs(self.clock() - numeric_time) > 300 or not re_full_nonce(nonce):
            raise PermissionError("Expired timestamp or invalid nonce")
        expected = sign(row["secret"], timestamp, nonce, method, path, body)
        if not hmac.compare_digest(expected, normalized.get("x-sea-signature", "")):
            raise PermissionError("Invalid signature")
        try:
            with self.db:
                self.db.execute("INSERT INTO nonces VALUES(?,?,?)", (client, nonce, numeric_time))
                self.db.execute("DELETE FROM nonces WHERE used_at<?", (int(self.clock()) - 600,))
        except sqlite3.IntegrityError as error:
            raise PermissionError("Replayed request") from error
        return client

    def publish(self, package, client):
        validate_package(package)
        body = canonical(package).decode()
        existing = self.db.execute("SELECT body FROM packages WHERE id=?", (package["package_id"],)).fetchone()
        if existing:
            if existing["body"] != body:
                raise ValueError("Package ID collision")
            return 200, {"package_id": package["package_id"], "state": "candidate", "idempotent": True}
        for parent in package["parent_ids"]:
            if not self.db.execute("SELECT 1 FROM packages WHERE id=?", (parent,)).fetchone():
                raise ValueError("Unknown parent package")
        with self.db:
            self.db.execute("INSERT INTO packages VALUES(?,?,?,?,?,?,?)",
                            (package["package_id"], package["revision"], json.dumps(package["parent_ids"]),
                             body, client, "candidate", now()))
        return 201, {"package_id": package["package_id"], "state": "candidate", "idempotent": False}

    def search(self, query, limit=5):
        query_terms = terms(query)
        ranked = []
        for row in self.db.execute("SELECT * FROM packages WHERE state IN ('candidate','active')"):
            package = json.loads(row["body"])
            overlap = len(query_terms & terms(package["problem"] + " " + " ".join(package["conditions"])))
            if overlap:
                feedback = self.db.execute("SELECT reward FROM community_feedback WHERE package=?", (row["id"],)).fetchall()
                mean = sum(item[0] for item in feedback) / len(feedback) if feedback else None
                ranked.append((overlap, mean if mean is not None else -.1, package, row["state"], len(feedback)))
        result = []
        for _, mean, package, state, count in sorted(ranked, key=lambda item: (-item[0], -item[1], item[2]["package_id"]))[:limit]:
            result.append({"package_id": package["package_id"], "problem": package["problem"],
                           "conditions": package["conditions"], "state": state,
                           "feedback_count": count, "mean_reward": None if mean == -.1 else mean})
        return result

    def get(self, package_id):
        row = self.db.execute("SELECT body,state FROM packages WHERE id=?", (package_id,)).fetchone()
        if not row:
            raise KeyError(package_id)
        return {"package": json.loads(row["body"]), "state": row["state"]}

    def feedback(self, package_id, client, task, reward, evidence_digest):
        if not self.db.execute("SELECT 1 FROM packages WHERE id=?", (package_id,)).fetchone():
            raise KeyError(package_id)
        if not isinstance(reward, (int, float)) or isinstance(reward, bool) or not 0 <= reward <= 1:
            raise ValueError("reward must be in [0,1]")
        if not task.strip() or not re_hex(evidence_digest):
            raise ValueError("Opaque task ID and SHA-256 evidence digest are required")
        with self.db:
            self.db.execute("INSERT INTO community_feedback VALUES(?,?,?,?,?,?)",
                            (package_id, client, task, reward, evidence_digest, now()))
            rows = self.db.execute("SELECT reward FROM community_feedback WHERE package=?", (package_id,)).fetchall()
            state = "active" if len(rows) >= 3 and min(row[0] for row in rows) >= .5 else "candidate"
            self.db.execute("UPDATE packages SET state=? WHERE id=?", (state, package_id))
        return {"package_id": package_id, "state": state, "feedback_count": len(rows),
                "mean_reward": sum(row[0] for row in rows) / len(rows)}

    def versions(self, package_id):
        self.get(package_id)
        rows = self.db.execute("SELECT body,state FROM packages").fetchall()
        children = []
        for row in rows:
            package = json.loads(row["body"])
            if package_id in package["parent_ids"]:
                children.append({"package_id": package["package_id"], "revision": package["revision"],
                                 "state": row["state"]})
        return {"package_id": package_id, "children": sorted(children, key=lambda item: item["package_id"])}

    def close(self):
        self.db.close()


def re_full_nonce(value):
    return isinstance(value, str) and len(value) == 32 and all(char in "0123456789abcdef" for char in value)


def re_hex(value):
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def create_app(registry):
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def dispatch(request: Request):
        path = request.url.path + (("?" + request.url.query) if request.url.query else "")
        body = await request.body()
        try:
            if request.method == "GET" and request.url.path == "/health":
                return JSONResponse({"status": "ok", "revision": "python-reference/1.0"})
            if request.method == "GET" and request.url.path == "/v1/policy":
                return JSONResponse({
                    "version": POLICY_VERSION, "package_schema": "sea-wisdom/1.0",
                    "maximum_body_bytes": 256000,
                    "stores": ["reviewed wisdom packages", "aggregate outcome feedback", "client identifiers",
                               "replay-prevention nonces"],
                    "excludes": ["raw conversations", "private files", "source code", "credentials",
                                 "personal identifiers", "raw execution traces"],
                    "reuse": "Packages may be searched, tested, revised, and redistributed to authenticated SEA clients.",
                })
            contribution = request.method == "POST"
            client = registry.authenticate(request.method, path, body, request.headers, contribution)
            payload = json.loads(body) if body else None
            if request.method == "POST" and request.url.path == "/v1/packages":
                code, response = registry.publish(payload, client)
            elif request.method == "GET" and request.url.path == "/v1/search":
                response, code = registry.search(request.query_params.get("q", ""),
                    min(20, max(1, int(request.query_params.get("limit", "5"))))), 200
            elif request.method == "GET" and request.url.path.startswith("/v1/packages/"):
                package_id = request.path_params["package_id"]
                if request.url.path.endswith("/versions"):
                    response = registry.versions(package_id)
                else:
                    response = registry.get(package_id)
                code = 200
            elif request.method == "POST" and request.url.path.startswith("/v1/feedback/"):
                response = registry.feedback(request.path_params["package_id"], client, payload["task"],
                                             payload["reward"], payload["evidence_digest"])
                code = 200
            else:
                return JSONResponse({"error": "Not found"}, status_code=404)
            return JSONResponse(response, status_code=code)
        except PermissionError as error:
            return JSONResponse({"error": str(error)}, status_code=401)
        except KeyError as error:
            return JSONResponse({"error": f"Not found: {error.args[0]}"}, status_code=404)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        except sqlite3.IntegrityError:
            return JSONResponse({"error": "Duplicate feedback"}, status_code=409)

    return Starlette(routes=[
        Route("/health", dispatch, methods=["GET"]),
        Route("/v1/policy", dispatch, methods=["GET"]),
        Route("/v1/packages", dispatch, methods=["POST"]),
        Route("/v1/search", dispatch, methods=["GET"]),
        Route("/v1/packages/{package_id}", dispatch, methods=["GET"]),
        Route("/v1/packages/{package_id}/versions", dispatch, methods=["GET"]),
        Route("/v1/feedback/{package_id}", dispatch, methods=["POST"]),
    ])


if __name__ == "__main__":
    import os
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="registry.sqlite3")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    registry = Registry(args.db)
    client_id, secret = os.getenv("SEA_BOOTSTRAP_CLIENT"), os.getenv("SEA_BOOTSTRAP_SECRET")
    if client_id and secret:
        registry.register_client(client_id, secret)
    uvicorn.run(create_app(registry), host=args.host, port=args.port)
