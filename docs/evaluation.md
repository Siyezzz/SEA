# Evaluation protocol — planned, not reported results

## Hypothesis

At a fixed model and total inference budget, evidence-gated, scoped memory improves future task success over no memory, a static skill, and indiscriminate memory accumulation, without materially reducing retained capability.

## Experimental design

1. Build chronological discovery, validation and sealed test splits of small coding/data tasks. Split by underlying task family, not just filenames or paraphrases. Include changed project conventions and explicit counterexamples.
2. Freeze model version, prompt, tool permissions, random seeds where supported, evaluator and budgets before testing. Keep sealed test answers unavailable to the memory writer. Freeze memory during final evaluation; online adaptation is a separate experimental arm.
3. Compare no memory, static core skill only, append-all history, ordinary similarity retrieval, and the proposed scope + evidence + budget system. Use equal total token/tool budgets including reflection and retrieval; also report matched active-context comparisons separately.
4. Randomize inclusion/exclusion of candidate memories on paired validation tasks where replay is safe. Repeat across seeds and report uncertainty on paired success differences. Do not validate deletion or external side effects against live user resources.
5. Measure success, regressions on old tasks, transfer across projects, token/cost/latency including memory maintenance, evidence recovery, irrelevant injection, and memory footprint. Reopen the database in a new process to test persistence.
6. Run ablations without evidence gates, scope filters, archive exclusion and original-evidence pointers. Include poisoned memory text to test whether the host treats retrieved text as instructions. This library does not enforce that host boundary itself.

## Falsification

Reject the proposed advantage if gains disappear under equal total budget, fail on held-out families, depend on leaked answers, or come with substantial regressions. Pre-register acceptable deltas and sample sizes after a separate pilot, before the sealed test. Do not retrospectively tune thresholds to test outcomes.

## Current executable checks

`python -m unittest discover -s tests -v` exercises promotion/regression, duplicate feedback, discovery-task exclusion, scope isolation, archive recovery, byte budgets, invalid rewards and persistence. `demo.py` uses synthetic rewards. Neither tests LLM behavior or establishes learning gains. There are currently no claimed benchmark scores.

Candidate selection tests additionally cover paired-report consistency, changed evaluators, baseline tampering, missing/duplicate task records, insufficient samples, retained-capability gates, Pareto tradeoffs and UCB1 exploration. `evolution_demo.py` is synthetic. See [algorithms](algorithms.md) for the fixed-sample assumptions and multiple-comparison limit. These checks establish implementation behavior, not autonomous learning gains.

## Trust and engineering limits

The CLI trusts the caller's evidence and task IDs. It cannot attest that feedback is external, correct or independent. An evaluator service with restricted write access is needed before autonomous promotion can be treated as meaningful. The SQLite event table supports inspection, not tamper-proof auditing. Memory files can contain sensitive task data and should stay local unless deliberately reviewed for sharing.

The kernel has no model adapter, worker scheduler, tokenizer, semantic compressor, filesystem executor, or permission enforcement layer. These are explicit future integration work, not hidden capabilities of SKILL.md.
