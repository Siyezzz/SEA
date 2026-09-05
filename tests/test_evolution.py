import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from evolution import evaluate, pareto_frontier, ucb_select
from evolution_demo import fixture


class EvolutionTests(unittest.TestCase):
    def test_evidence_gate_and_retention(self):
        results = {r["revision"]: r for r in evaluate(fixture())["decisions"]}
        self.assertEqual(results["better-core"]["decision"], "eligible")
        self.assertEqual(results["cheap-runner"]["decision"], "eligible")
        self.assertEqual(results["forgetful-selector"]["decision"], "hold")

    def test_small_sample_does_not_establish_gain(self):
        self.assertTrue(all(r["decision"] == "hold" for r in evaluate(fixture(3))["decisions"]))

    def test_changed_evaluator_rejected(self):
        data = fixture(3)
        data["candidates"][0]["evaluator_revision"] = "easier-grader"
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_changed_baseline_observations_rejected(self):
        data = fixture(3)
        data["candidates"][1]["trials"][0]["baseline_quality"] = 0
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_leakage_missing_and_duplicate_tasks_rejected(self):
        for mutation in ("leak", "missing", "duplicate"):
            data = fixture(3)
            candidate = data["candidates"][0]
            if mutation == "leak":
                candidate["discovery_task_ids"].append("new-0")
            elif mutation == "missing":
                candidate["trials"].pop()
            else:
                candidate["trials"].append(candidate["trials"][0])
            with self.assertRaises(ValueError):
                evaluate(data)

    def test_invalid_numbers_and_comparison_budget(self):
        for value in (float("nan"), float("inf"), -1, 2, True):
            data = fixture(3)
            data["candidates"][0]["trials"][0]["candidate_quality"] = value
            with self.assertRaises(ValueError):
                evaluate(data)
        data = fixture(3)
        data["contract"]["comparison_limit"] = 2
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_pareto_keeps_tradeoffs_and_removes_dominated(self):
        self.assertEqual(pareto_frontier({"accurate": (.9, -.8), "cheap": (.7, -.1),
                                         "worse": (.6, -.9)}), ["accurate", "cheap"])

    def test_ucb_explores_and_then_uses_evidence(self):
        self.assertEqual(ucb_select({"known": [1], "new": []}), "new")
        self.assertEqual(ucb_select({"good": [1] * 20, "bad": [0] * 20}), "good")
        self.assertEqual(ucb_select({"good": [1] * 100, "uncertain": [.5]}), "uncertain")

    def test_component_names_are_not_a_fixed_allowlist(self):
        data = fixture()
        data["candidates"][0]["component"] = "evolution-mechanism-itself"
        self.assertEqual(evaluate(data)["decisions"][0]["decision"], "eligible")

    def test_contract_digest_changes_with_evaluation_design(self):
        data = fixture(3)
        before = evaluate(data)["contract_sha256"]
        data["contract"]["cost_weight"] = .2
        self.assertNotEqual(before, evaluate(data)["contract_sha256"])

    def test_cli_reads_a_report_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            original = json.dumps(fixture(3))
            path.write_text(original, encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "evolution.py"
            result = subprocess.run([sys.executable, str(script), str(path)],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(len(json.loads(result.stdout)["decisions"]), 3)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
