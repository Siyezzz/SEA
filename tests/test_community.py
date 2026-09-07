import hashlib
import json
import secrets
import tempfile
import time
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from community import (COMPONENT, DEFAULT_REVISION, build_package, evolve_sync_policy,
                       privacy_findings, queue_memory, sign, sync_pending)
from evolution_demo import fixture
from kernel import Kernel
from registry import Registry, create_app
from usage import POLICY_VERSION, acknowledge


SECRET = "synthetic-secret-for-tests"


class DirectTransport:
    def __init__(self, registry, client="client-a", secret=SECRET):
        self.registry, self.client, self.secret = registry, client, secret

    def request(self, method, path, payload=None):
        body = b"" if payload is None else json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        timestamp, nonce = str(int(time.time())), secrets.token_hex(16)
        headers = {"X-SEA-Client": self.client, "X-SEA-Timestamp": timestamp, "X-SEA-Nonce": nonce,
                   "X-SEA-Signature": sign(self.secret, timestamp, nonce, method, path, body),
                   "X-SEA-Policy-Version": POLICY_VERSION}
        try:
            client = self.registry.authenticate(method, path, body, headers, contribution=method == "POST")
            if method == "POST" and path == "/v1/packages":
                return self.registry.publish(payload, client)
            if method == "POST" and path.startswith("/v1/feedback/"):
                return 200, self.registry.feedback(path.rsplit("/", 1)[-1], client, payload["task"],
                                                   payload["reward"], payload["evidence_digest"])
        except (ValueError, PermissionError, KeyError) as error:
            return 400, {"error": str(error)}
        raise AssertionError(path)


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.kernel = Kernel()
        acknowledge(self.kernel, POLICY_VERSION, "community-contribute", "synthetic:test", True)
        self.mid = self.kernel.add("alpha", "CSV encoding", "Inspect encoding before parsing",
                                   "synthetic:discovery", "discovery")
        for index in range(3):
            self.kernel.feedback(self.mid, f"heldout-{index}", 1, f"synthetic:{index}")
        self.registry = Registry()
        self.registry.register_client("client-a", SECRET)

    def tearDown(self):
        self.kernel.close()
        self.registry.close()

    def test_private_content_rejected_before_queue(self):
        self.assertTrue(privacy_findings({"method": "email me at person@example.com"}))
        private = self.kernel.add("alpha", "Credentials", "Use api_key=private-value", "x", "d")
        for index in range(3):
            self.kernel.feedback(private, f"p-{index}", 1, "synthetic")
        with self.assertRaisesRegex(ValueError, "privacy"):
            queue_memory(self.kernel, private, [], [], {"models": [], "tools": [], "environments": []})
        self.assertEqual(self.kernel.db.execute("SELECT count(*) FROM community_outbox").fetchone()[0], 0)

    def test_outbox_signed_publish_is_idempotent(self):
        queued = queue_memory(self.kernel, self.mid, ["Python"], ["Known UTF-8 fixture"],
                              {"models": ["model-family"], "tools": ["python"], "environments": ["test"]})
        result = sync_pending(self.kernel, DirectTransport(self.registry))
        self.assertEqual(result["results"][0]["state"], "sent")
        self.assertEqual(self.registry.get(queued["package_id"])["state"], "candidate")
        self.assertEqual(sync_pending(self.kernel, DirectTransport(self.registry))["results"], [])
        package = self.registry.get(queued["package_id"])["package"]
        code, response = self.registry.publish(package, "client-a")
        self.assertEqual((code, response["idempotent"]), (200, True))

    def test_registry_feedback_search_and_lineage(self):
        first = queue_memory(self.kernel, self.mid, ["Python CSV"], [],
                             {"models": [], "tools": ["python"], "environments": []})["package_id"]
        sync_pending(self.kernel, DirectTransport(self.registry))
        for index in range(3):
            client = f"validator-{index}"
            secret = SECRET + str(index)
            self.registry.register_client(client, secret)
            result = DirectTransport(self.registry, client, secret).request("POST", f"/v1/feedback/{first}", {
                "task": f"opaque-{index}", "reward": 1,
                "evidence_digest": hashlib.sha256(f"evidence-{index}".encode()).hexdigest()})
            self.assertEqual(result[0], 200)
        self.assertEqual(self.registry.get(first)["state"], "active")
        metadata = self.registry.search("Python CSV")
        self.assertEqual(metadata[0]["package_id"], first)
        self.assertNotIn("method", metadata[0])
        memory = self.kernel.get(self.mid)
        rewards = [1, 1, 1]
        child = build_package(memory, rewards, ["Python CSV"], ["new edge case"],
                              {"models": [], "tools": ["python"], "environments": []}, [first], 2)
        self.registry.publish(child, "client-a")
        self.assertEqual(self.registry.versions(first)["children"][0]["package_id"], child["package_id"])

    def test_signature_replay_and_tamper_rejected(self):
        body = b"{}"
        timestamp, nonce, path = str(int(time.time())), "a" * 32, "/v1/packages"
        headers = {"X-SEA-Client": "client-a", "X-SEA-Timestamp": timestamp, "X-SEA-Nonce": nonce,
                   "X-SEA-Signature": sign(SECRET, timestamp, nonce, "POST", path, body),
                   "X-SEA-Policy-Version": POLICY_VERSION}
        self.registry.authenticate("POST", path, body, headers, contribution=True)
        with self.assertRaisesRegex(PermissionError, "Replayed"):
            self.registry.authenticate("POST", path, body, headers, contribution=True)
        headers["X-SEA-Nonce"] = "b" * 32
        with self.assertRaisesRegex(PermissionError, "signature"):
            self.registry.authenticate("POST", path, b'{"changed":true}', headers, contribution=True)

    def test_sync_policy_evolves_only_with_independent_eligible_report(self):
        report = fixture()
        candidate = report["candidates"][0]
        candidate["component"], candidate["revision"] = COMPONENT, "community-sync-policy/1.1"
        report["candidates"] = [candidate]
        result = evolve_sync_policy(self.kernel, report, candidate["revision"], DEFAULT_REVISION,
                                    "sha256:synthetic-artifact", {"batch_size": 20, "max_attempts": 4})
        self.assertEqual(result["active_revision"], candidate["revision"])
        states = dict(self.kernel.db.execute("SELECT revision,state FROM component_versions"))
        self.assertEqual(states[DEFAULT_REVISION], "predecessor")
        self.assertEqual(states[candidate["revision"]], "active")
        with self.assertRaises(ValueError):
            evolve_sync_policy(self.kernel, report, "another", DEFAULT_REVISION, "x",
                               {"batch_size": 100, "max_attempts": 4})

    def test_real_asgi_route_requires_signed_request(self):
        package = build_package(self.kernel.get(self.mid), [1, 1, 1], ["Python"], [],
                                {"models": [], "tools": [], "environments": []})
        body = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path, timestamp, nonce = "/v1/packages", str(int(time.time())), "c" * 32
        headers = {"X-SEA-Client": "client-a", "X-SEA-Timestamp": timestamp, "X-SEA-Nonce": nonce,
                   "X-SEA-Signature": sign(SECRET, timestamp, nonce, "POST", path, body),
                   "X-SEA-Policy-Version": POLICY_VERSION, "Content-Type": "application/json"}
        with TestClient(create_app(self.registry)) as client:
            policy = client.get("/v1/policy")
            self.assertEqual(policy.status_code, 200)
            self.assertEqual(policy.json()["version"], POLICY_VERSION)
            response = client.post(path, content=body, headers=headers)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(client.post(path, content=body).status_code, 401)


if __name__ == "__main__":
    unittest.main()
