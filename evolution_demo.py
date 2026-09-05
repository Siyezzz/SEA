"""Synthetic selection demonstration. No LLM learning or source edits occur."""
import argparse
import json
from evolution import evaluate


def fixture(n=200):
    contract = {"suite": "synthetic-v1", "baseline_revision": "seed",
                "evaluator_revision": "synthetic-evaluator-v1", "alpha": .05,
                "cost_weight": .1, "minimum_gain": .01, "retention_tolerance": .25,
                "comparison_limit": 3, "task_ids": [f"new-{i}" for i in range(n)],
                "retention_task_ids": [f"old-{i}" for i in range(n)]}
    candidates = []
    for revision, component, quality, cost, retention in (
        ("better-core", "experience-core", .95, .3, .9),
        ("cheap-runner", "runner", .7, .1, .9),
        ("forgetful-selector", "candidate-selector", .99, .5, .1),
    ):
        candidates.append({"revision": revision, "component": component,
            "suite": contract["suite"], "baseline_revision": "seed",
            "evaluator_revision": contract["evaluator_revision"], "discovery_task_ids": ["discovery"],
            "trials": [{"task_id": task, "baseline_quality": .2, "candidate_quality": quality,
                        "baseline_cost": .5, "candidate_cost": cost, "evidence": "synthetic:fixture"}
                       for task in contract["task_ids"]],
            "retention_trials": [{"task_id": task, "baseline_quality": .9,
                                  "candidate_quality": retention, "evidence": "synthetic:retention"}
                                 for task in contract["retention_task_ids"]]})
    return {"contract": contract, "candidates": candidates,
            "operator_rewards": {"rewrite-core": [.6, .7], "change-runner": [], "change-selector": [.1]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="store_true", help="Print example input JSON instead of decisions")
    args = parser.parse_args()
    print(json.dumps(fixture() if args.input else evaluate(fixture()), indent=2))
