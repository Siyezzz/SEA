"""Real STDIO protocol tests with temporary databases and synthetic evidence."""
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
import tempfile
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from evolution import evaluate
from evolution_demo import fixture

ROOT = Path(__file__).resolve().parents[1]

@asynccontextmanager
async def client(db, acknowledge_fixture=True):
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "sea_mcp.py"), "--db", str(db)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if acknowledge_fixture:
                from usage import POLICY_VERSION
                result = await session.call_tool("acknowledge_usage", dict(version=POLICY_VERSION,
                    mode="local-only", source="Synthetic test fixture acknowledgement, not a real user.",
                    user_acknowledged=True))
                assert not result.isError, result
            yield session

def decoded(result):
    if result.isError:
        raise AssertionError(result.content)
    return json.loads(result.content[0].text)

class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_onboarding_requires_explicit_choice_and_survives_restart(self):
        from usage import POLICY_VERSION
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "memory.sqlite3"
            async with client(db, acknowledge_fixture=False) as c:
                initial = decoded(await c.call_tool("get_usage_status", {}))
                self.assertFalse(initial["acknowledged"])
                self.assertFalse(initial["sharing_active"])
                self.assertEqual(initial["registry"], {"configured": False, "url": None})
                self.assertEqual(initial["notice"]["recommended_mode"], "community-contribute")
                for tool, args in (("get_preferences", dict(project="a")),
                    ("record_candidate", dict(project="a", trigger="x", lesson="x", evidence="x", origin="x")),
                    ("compare_candidates", dict(report_json=json.dumps(fixture(5))))):
                    self.assertTrue((await c.call_tool(tool, args)).isError)
                for version, confirmed in ((POLICY_VERSION, False), ("old-version", True)):
                    self.assertTrue((await c.call_tool("acknowledge_usage", dict(version=version,
                        mode="community-contribute", source="synthetic", user_acknowledged=confirmed))).isError)
                self.assertFalse(decoded(await c.call_tool("get_usage_status", {}))["acknowledged"])
                accepted = decoded(await c.call_tool("acknowledge_usage", dict(version=POLICY_VERSION,
                    mode="community-contribute", source="synthetic:explicit-choice", user_acknowledged=True)))
                self.assertTrue(accepted["acknowledged"])
                self.assertFalse(accepted["sharing_active"])
                self.assertFalse((await c.call_tool("get_preferences", dict(project="a"))).isError)
            async with client(db, acknowledge_fixture=False) as c:
                current = decoded(await c.call_tool("get_usage_status", {}))
                self.assertEqual(current["choice"]["mode"], "community-contribute")
                changed = decoded(await c.call_tool("acknowledge_usage", dict(version=POLICY_VERSION,
                    mode="local-only", source="synthetic:withdrawal", user_acknowledged=True)))
                self.assertEqual(changed["choice"]["mode"], "local-only")

    async def test_lifecycle_scopes_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "memory.sqlite3"
            async with client(db) as c:
                self.assertEqual(len((await c.list_tools()).tools), 18)
                candidate = decoded(await c.call_tool("record_candidate", dict(
                    project="alpha", trigger="CSV encoding", lesson="Inspect encoding",
                    evidence="synthetic:discovery", origin="discovery")))
                mid = candidate["id"]
                r = await c.call_tool("recall", dict(query="CSV", project="alpha"))
                self.assertFalse(r.isError)
                self.assertEqual(r.content[0].text, "")
                for tool, args in (("get_memory", dict(project="beta", memory_id=mid)),
                    ("record_feedback", dict(project="beta", memory_id=mid,
                        task="v1", reward=1, evidence="synthetic"))):
                    self.assertTrue((await c.call_tool(tool, args)).isError)
                for task in ("v1", "v2", "v3"):
                    result = decoded(await c.call_tool("record_feedback", dict(
                        project="alpha", memory_id=mid, task=task, reward=1, evidence="synthetic:" + task)))
                self.assertEqual(result["state"], "active")
                self.assertTrue((await c.call_tool("record_feedback", dict(
                    project="alpha", memory_id=mid, task="v3", reward=1, evidence="duplicate"))).isError)
            async with client(db) as c:
                r = await c.call_tool("recall", dict(query="CSV", project="alpha"))
                self.assertIn(mid, r.content[0].text)
                self.assertEqual(decoded(await c.call_tool("archive_project", dict(project="alpha"))), {"archived": 1})
                self.assertFalse((await c.call_tool("recall", dict(query="CSV", project="alpha"))).content[0].text)
                r = await c.call_tool("recall", dict(query="CSV", project="alpha", include_archived=True))
                self.assertIn(mid, r.content[0].text)
                self.assertTrue((await c.call_tool("archive_project", dict(project="global"))).isError)
                self.assertTrue((await c.call_tool("search_community", dict(query="CSV"))).isError)

    async def test_preferences_validation_budget_and_pagination(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "memory.sqlite3"
            async with client(db) as c:
                item = decoded(await c.call_tool("record_preference", dict(
                    project="global", key="style", value="Use the chat box", source="synthetic:user-statement")))
                self.assertEqual(item["kind"], "user_stated_preference")
                for args in (dict(project="a", budget=-1), dict(project="a", budget=999999)):
                    self.assertTrue((await c.call_tool("get_preferences", args)).isError)
                self.assertFalse((await c.call_tool("get_preferences", dict(project="a", budget=1))).content[0].text)
                self.assertTrue((await c.call_tool("record_candidate", dict(
                    project="a", trigger=" ", lesson="x", evidence="x", origin="x"))).isError)
                for i in range(3):
                    decoded(await c.call_tool("record_candidate", dict(
                        project="a", trigger="csv", lesson=str(i), evidence="synthetic", origin="d")))
                page = decoded(await c.call_tool("inspect_learning", dict(project="a", limit=2)))
                self.assertEqual(len(page["items"]), 2)
                self.assertEqual(page["next_offset"], 2)
                self.assertNotIn("evidence", page["items"][0])
                page2 = decoded(await c.call_tool("inspect_learning", dict(project="a", limit=2, offset=2)))
                self.assertIsNone(page2["next_offset"])
            async with client(db) as c:
                prefs = await c.call_tool("get_preferences", dict(project="other"))
                self.assertIn("Use the chat box", prefs.content[0].text)
                self.assertLessEqual(len(prefs.content[0].text.encode()), 2048)

    async def test_comparison_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            async with client(Path(directory) / "memory.sqlite3") as c:
                report = fixture(5)
                result = decoded(await c.call_tool("compare_candidates", dict(report_json=json.dumps(report))))
                self.assertEqual(result, evaluate(report))
                self.assertTrue((await c.call_tool("compare_candidates", dict(report_json="{}"))).isError)
