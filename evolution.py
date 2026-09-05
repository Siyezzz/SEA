"""Offline candidate selection primitives; never executes or rewrites candidates."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def unit(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Expected a finite number in [0, 1]")
    return value


def label(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a nonempty identifier")
    return value


def unique_ids(values):
    if not isinstance(values, list) or not values:
        raise ValueError("Expected a nonempty list of task IDs")
    ids = [label(v) for v in values]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate task IDs")
    return set(ids)


def ucb_select(rewards):
    """UCB1 for stationary bounded rewards; use only for experiment allocation."""
    if not rewards:
        raise ValueError("At least one operator is required")
    for name, history in rewards.items():
        label(name)
        if not isinstance(history, list):
            raise ValueError("Operator history must be a list")
        for reward in history:
            unit(reward)
    untried = sorted(name for name, history in rewards.items() if not history)
    if untried:
        return untried[0]
    total = sum(len(history) for history in rewards.values())
    scores = {name: sum(history) / len(history) + math.sqrt(2 * math.log(total) / len(history))
              for name, history in rewards.items()}
    return min(scores, key=lambda name: (-scores[name], name))


def pareto_frontier(points):
    """All coordinates are maximized; negate cost before passing it here."""
    if not points:
        return []
    dimensions = len(next(iter(points.values())))
    if not dimensions:
        raise ValueError("At least one objective is required")
    for name, vector in points.items():
        label(name)
        if len(vector) != dimensions or any(not math.isfinite(x) for x in vector):
            raise ValueError("Objectives must be finite and have matching dimensions")
    def dominates(a, b):
        return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))
    return sorted(name for name, vector in points.items()
                  if not any(dominates(other, vector) for other in points.values()))


def lower_bound(values, width, alpha):
    # One-sided Hoeffding bound for one fixed, independent evaluation batch.
    return sum(values) / len(values) - width * math.sqrt(math.log(1 / alpha) / (2 * len(values)))


def evaluate(document):
    """Validate paired reports and return decisions, a frontier, and an operator."""
    contract = document["contract"]
    for key in ("suite", "baseline_revision", "evaluator_revision"):
        label(contract[key])
    task_ids = unique_ids(contract["task_ids"])
    retention_ids = unique_ids(contract["retention_task_ids"])
    if task_ids & retention_ids:
        raise ValueError("Adaptation and retention tasks must be disjoint")
    alpha = unit(contract["alpha"])
    if not 0 < alpha < 1:
        raise ValueError("Alpha must be strictly between zero and one")
    weight = unit(contract["cost_weight"])
    margin = unit(contract["minimum_gain"])
    tolerance = unit(contract["retention_tolerance"])
    limit = contract["comparison_limit"]
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Comparison limit must be a positive integer")
    candidates = document["candidates"]
    if not candidates or len(candidates) > limit:
        raise ValueError("Candidate count must be within the registered comparison limit")
    digest = hashlib.sha256(json.dumps(contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
    results, points, seen, baseline_records = [], {}, set(), {}
    for candidate in candidates:
        revision = label(candidate["revision"])
        component = label(candidate["component"])
        if revision in seen or revision == contract["baseline_revision"]:
            raise ValueError("Candidate revisions must be unique and differ from baseline")
        seen.add(revision)
        if candidate["suite"] != contract["suite"] or candidate["evaluator_revision"] != contract["evaluator_revision"]:
            raise ValueError("Evaluator and suite must match the comparison contract")
        if candidate["baseline_revision"] != contract["baseline_revision"]:
            raise ValueError("Baseline revision mismatch")
        discovery = candidate["discovery_task_ids"]
        if not isinstance(discovery, list) or any(not isinstance(x, str) or not x.strip() for x in discovery):
            raise ValueError("Discovery task IDs must be a list of nonempty strings")
        if set(discovery) & (task_ids | retention_ids):
            raise ValueError("Discovery tasks overlap evaluation tasks")
        gains, retained, qualities, costs, old_quality = [], [], [], [], []
        for key, expected in (("trials", task_ids), ("retention_trials", retention_ids)):
            trials = candidate[key]
            actual = unique_ids([row["task_id"] for row in trials])
            if actual != expected:
                raise ValueError("Missing or unexpected evaluation tasks")
            for row in trials:
                label(row["evidence"])
                baseline = unit(row["baseline_quality"])
                quality = unit(row["candidate_quality"])
                baseline_key = (key, row["task_id"])
                baseline_value = (baseline, unit(row["baseline_cost"])) if key == "trials" else (baseline,)
                if baseline_key in baseline_records and baseline_records[baseline_key] != baseline_value:
                    raise ValueError("Baseline observations must match across candidates")
                baseline_records[baseline_key] = baseline_value
                if key == "trials":
                    base_cost = unit(row["baseline_cost"])
                    cost = unit(row["candidate_cost"])
                    gains.append(quality - baseline - weight * (cost - base_cost))
                    qualities.append(quality)
                    costs.append(cost)
                else:
                    retained.append(quality - baseline)
                    old_quality.append(quality)
        # Union bound over two claims for every pre-registered comparison.
        per_claim = alpha / (2 * limit)
        gain_lcb = lower_bound(gains, 2 * (1 + weight), per_claim)
        retention_lcb = lower_bound(retained, 2, per_claim)
        decision = "eligible" if gain_lcb > margin and retention_lcb >= -tolerance else "hold"
        results.append({"revision": revision, "component": component, "decision": decision,
                        "mean_gain": sum(gains) / len(gains), "gain_lower_bound": gain_lcb,
                        "retention_lower_bound": retention_lcb,
                        "trials": len(gains), "retention_trials": len(retained)})
        points[revision] = (sum(qualities) / len(qualities),
                            -sum(costs) / len(costs), sum(old_quality) / len(old_quality))
    return {"contract_sha256": digest, "decisions": results,
            "observed_pareto_frontier": pareto_frontier(points),
            "next_operator": ucb_select(document["operator_rewards"]),
            "notice": "Offline report only. Evidence authenticity and independence are caller responsibilities. No candidate was executed or installed."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="JSON paired evaluation report")
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.report.read_text(encoding="utf-8-sig"))), indent=2))


if __name__ == "__main__":
    main()
