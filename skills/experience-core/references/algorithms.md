# Candidate selection algorithms

`evolution.py` implements small, dependency-free primitives. They consume externally produced evaluation records; they do not call a model, generate patches, authenticate evidence, or install a successor. The original memory gate in `kernel.py` remains unchanged and heuristic. Candidate comparison is a separate API, not an automatic replacement for memory promotion.

## 1. Paired quality and cost gain

For task i, quality q and normalized total cost c are both in [0, 1]. Fix the cost scale and weight before evaluating a candidate:

$$d_i = (q_i^{candidate} - q_i^{baseline}) - \lambda(c_i^{candidate} - c_i^{baseline}).$$

The implementation accepts 0 <= lambda <= 1. Costs should include inference, reflection, retrieval, candidate generation, and testing, using a predeclared allocation rule for shared costs. Supply bounded, normalized values; out-of-range or non-finite values are rejected instead of silently clipped. A poor choice of cost scale remains the caller's responsibility.

This is SEA's explicit engineering objective, informed by empirical candidate evaluation in [DGM](https://arxiv.org/abs/2505.22954). It is not a formula claimed as an invention of DGM or a causal estimator by itself. Paired experiments need controlled conditions or randomized treatment assignment to support causal interpretations.

## 2. Uncertainty-aware eligibility

For independent bounded observations with range width R, a one-sided Hoeffding lower bound is:

$$LCB = \bar d - R\sqrt{\frac{\log(1/\delta)}{2n}}.$$

Here d lies in [-(1+lambda), 1+lambda], so R = 2(1+lambda). Old-task quality differences have width 2. The method follows the bounded-variable concentration result in [Hoeffding, 1963](https://doi.org/10.1080/01621459.1963.10500830). This bound can be very conservative; it does not assume that three successes prove generalization.

For at most K predeclared comparisons and two claims per comparison, use delta = alpha/(2K). A union bound controls the family of claims **only under the sampling assumptions and fixed evaluation plan**. Eligibility requires:

$$LCB_{gain} > minimum\_gain,\qquad LCB_{retention} \ge -retention\_tolerance.$$

Anything else returns `hold`, meaning do not promote on this evidence. It may represent insufficient data or actual harm. No automatic deployment follows an `eligible` result.

The report checks matching task sets, duplicate IDs, discovery/evaluation overlap, shared baseline observations, evaluator identity, and comparison count. Contract hashing identifies the supplied design; it is not a signature, an access-control boundary, or proof of pre-registration. Different IDs do not prove independence. Correlated paraphrases and reused test sets invalidate the naive interpretation. Select candidates on development data, freeze them, then use fresh independent evaluation tasks. Repeated peeking and adaptive reuse across CLI calls require a separate sequential-testing or alpha-spending design, which is not implemented.

## 3. Pareto preservation

Candidate a dominates b if it is at least as good in every objective and strictly better in at least one:

$$a \succ b \iff (\forall j, f_j(a) \ge f_j(b))\land(\exists j, f_j(a)>f_j(b)).$$

Keep all non-dominated candidates, using mean new-task quality, negative mean cost, and mean old-task quality. This retains tradeoffs without requiring a single permanent weighting. The implementation is O(m squared times objectives) for m candidates, suitable for small archives.

[GEPA](https://arxiv.org/abs/2507.19457) motivates preserving complementary variants, but SEA's aggregate objective frontier differs from GEPA's per-instance Pareto machinery. The output is an **observed** frontier, not a statistically established ranking. A held candidate may remain on the frontier; frontier membership does not override eligibility. This distinction lets a useful research alternative survive without deploying it.

## 4. UCB1 for experiment allocation

For operator j with n_j observations and bounded rewards, select the largest index:

$$UCB_j = \bar r_j + \sqrt{\frac{2\log t}{n_j}}.$$

Untried operators are selected first with deterministic name ordering. This is [UCB1, Auer et al., 2002](https://doi.org/10.1023/A:1013689704352). It balances observed reward with uncertainty. Use it to allocate experiments among such operators as rewriting the core, improving retrieval, or changing the runner; it does not authorize executing the chosen operator.

Rewards must be measured and normalized to [0, 1] with a fixed rule. Define them from validated improvement per fixed-budget attempt, not self-reported novelty. Failed attempts belong in the history. UCB1 assumes stationary bounded reward distributions; changing operators or task distributions breaks its usual guarantees. Start a separately identified history after a substantive operator revision. The CLI trusts the provided histories and does not persist them.

## Run the synthetic example

```bash
python evolution_demo.py
python evolution_demo.py --input > comparison.json
python evolution.py comparison.json
```

`comparison.json` is an example evaluation input, not an executable candidate. The demo prints results for synthetic core, runner, and selector variants. Component names are unrestricted nonempty identifiers so that the selection mechanism itself can also be evaluated.

The fixture deliberately uses large artificial gains and a permissive retention tolerance of 0.25 to demonstrate all branches with 200 records. Those values are **not recommended deployment thresholds**. Repeated synthetic rows are not independent empirical evidence, and the printed bounds are only an arithmetic demonstration. Unit tests also confirm that a three-record fixture cannot pass the gate, that old-task degradation blocks eligibility, and that changed graders or incomplete task reports are rejected.

## Minimal host contract

Generate the example input above for the full schema. The contract identifies the suite, baseline and evaluator revisions, new/old task IDs, comparison limit, alpha, quality margin, retention tolerance and cost weight. Each candidate identifies its revision and component plus paired trials with quality, cost and evidence references. All candidates use the same cached baseline observations. Operators have separate bounded reward histories.

The host must store these revision identifiers against actual source artifacts, authenticate evaluator output, allocate a real execution budget, and preserve predecessors. SHA-256 hashing the contract alone does not do those jobs. Evaluator candidates should be tested on an independently fixed calibration suite; changing the grader midway through a task-agent comparison is rejected.
