<p align="center"><img src="assets/sea-icon.svg" width="96" height="96" alt="SEA wave" /></p>

# SEA — Self-Evolving Agent

An evidence-driven experience kernel for agents that learn reusable strategies from interaction, without creating a new skill for every task.

**Status: runnable local experience memory, MCP tools, Codex plugin integration, and a deployable authenticated community registry. No demonstrated autonomous learning gains yet. No standalone LLM adapter, automatic evaluator, or background scheduler is included.**

## Why SEA?

Foundation models already have general knowledge and can solve unfamiliar tasks. What is often missing after deployment is a persistent learning loop: capture experience, test a proposed lesson, retain useful changes, and retrieve them when they matter.

We define useful self-evolution operationally: persistent changes derived from earlier interactions improve quality or reduce cost on unseen future tasks while retaining previous capabilities. This may happen in external memory or agent programs without updating model weights. It does not imply consciousness or unbounded improvement.

Read the [research notes](docs/research.md), [evaluation protocol](docs/evaluation.md), and [core skill](skills/experience-core/SKILL.md).

The [related-work comparison](docs/related-work.md) maps nine GitHub systems to concrete adoption decisions. The [algorithm reference](docs/algorithms.md) documents paired utility, uncertainty bounds, Pareto preservation, and UCB1 experiment allocation, including assumptions and limitations.

The [shared-learning architecture](docs/shared-learning.md) records individual specialization, controlled experience exchange, progressive disclosure, and the first two-instance transfer experiment. For conversation-first usage, see [SEA in the Codex chat interface](docs/codex-chat.md). The local MCP client and reference Cloudflare registry are implemented; see [community registry operations](docs/community-registry.md).

**Community contribution is the recommended onboarding choice, activated only by explicit acknowledgement and authenticated registry configuration.** SEA sends only a reviewed, schema-limited wisdom package after `prepare_contribution` and `sync_contributions`; ordinary memory operations do not transmit data. See [usage and sharing](docs/usage-and-sharing.md), [other MCP clients](docs/mcp-clients.md), and [the wave identity and remote-environment decision](docs/branding-and-environments.md).

The owner-operated reference registry is live at `https://sea-community-registry.li-siye-0123.workers.dev`. Its public `/v1/policy` endpoint reports the current service policy before a client is enrolled. Other deployments can use the same protocol and choose a different registry.

## Quick start

For chat usage, ask Codex to install the local SEA plugin following [the integration guide](docs/codex-chat.md), then say **"Use SEA for this task."** No daily terminal interaction is required.

For development: Python 3.10 or later. The memory and comparison runtimes use only the standard library. MCP integration and its tests require `pip install -r requirements-mcp.txt`. Local memory operations make no network requests. Community tools contact only the configured registry.

```bash
python demo.py
python evolution_demo.py
python -m unittest discover -s tests -v
python kernel.py --help
```

The demo uses **synthetic rewards** to illustrate state transitions. It is not a learning benchmark.

```bash
python kernel.py add --project demo --trigger "CSV encoding" --lesson "Inspect encoding before parsing CSV" --evidence "fixture:encoding" --origin discovery-1
# Replace ID with the returned memory ID. Each task must be an independent validation case.
python kernel.py feedback --id ID --task holdout-1 --reward 1 --evidence "test:holdout-1:passed"
python kernel.py recall "CSV encoding" --project demo --budget 2048
python kernel.py archive demo
python kernel.py recall "CSV encoding" --project demo --include-archived
```

The default database is `memory.sqlite3` in the working directory and is excluded from Git. Promotion requires at least three distinct validation task IDs, every reward at least 0.5, and a smoothed mean at least 0.7. Counterexamples can demote a lesson. These are prototype heuristics, not statistical significance criteria. Evidence strings and task independence must be verified by the caller.

## Architecture

```mermaid
flowchart LR
    A[Task and environmental feedback] --> B[Candidate lesson and provenance]
    B --> C[Independent validation]
    C --> D[Reusable strategy]
    D --> E[Relevance and utility retrieval]
    E --> A
    C --> F[Counterexamples and demotion]
    D --> G[Project archive]
    G --> H[Explicit lookup and revalidation]
```

| Component | Implemented | Future work |
|---|---|---|
| Core skill | Tool-first protocol and local Codex plugin packaging | Portable distribution and lifecycle integration |
| Persistent memory | SQLite, explicit preferences, provenance, project scope, events | Contradiction links, temporal validity, original evidence storage |
| Validation gate | Task ID deduplication, discovery-task exclusion, demotion | Trusted evaluators, statistical tests, causal attribution |
| Context selection | Lexical relevance, utility ranking, whole-record budget | Semantic retrieval, model tokenizer, task-state compiler |
| Lifecycle | Project archive and explicit lookup | Automatic distillation, reactivation workflow, skill generation |
| Exploration | Budgeted experiment guidance in the skill | Scheduler, real environment experiments, isolated execution |
| Candidate selection | Offline paired comparison, retention bounds, Pareto frontier, UCB1 allocation | Trusted execution reports, persistent program archive, automatic successor handover |
| Community exchange | Privacy-screened packages, local outbox, HMAC authentication, replay protection, progressive fetch, aggregate feedback, lineage | Withdrawal, abuse controls, semantic retrieval, federated operation |

The budget limits **UTF-8 bytes of returned text**, not model tokens or the surrounding prompt. Records that do not fit are skipped intact. Retrieval scans project records and therefore grows in cost with memory size. English word and CJK character matching is a dependency-free baseline, not semantic retrieval.

## Agent integration

The host calls `recall` before a task, checks applicability and evidence, records candidates after meaningful outcomes, and submits `feedback` from external tests. Loading the skill alone does not schedule these actions. Candidates are excluded from normal retrieval; an experiment controller can inspect them through `Kernel.get(id)`.

The repository supplies a local MCP server and a configuration script for Codex plugin scaffolds. Installation is explicit and machine-local; cloning alone does not connect a host. The kernel does not execute stored code or enforce system permissions; the host remains responsible for file, network, and tool boundaries. User preferences are stored separately from empirical lessons and never require fabricated validation rewards.

## Research direction

**Design principle: every component is a potential subject of evolution.** This includes the task agent, memory kernel, core skill, runner, scheduler, learning procedure, and evaluation methodology. The runner is an initial implementation, not a permanently privileged layer outside the learning loop. Evolvability does not grant permission to change host settings or bypass user constraints. Changes to evaluation must be validated against independent evidence; changing a score definition is not evidence of improved capability. See [recursive evolution](docs/research.md#7-recursive-evolution-without-a-permanently-fixed-runner).

Our proposed combination is to allocate memory by future decision value, promote lessons using counterfactual benefit, and support compression with recoverable evidence. Each component has precedents; SEA does not claim to invent self-evolution, hierarchical memory, or skill archival.

The first milestone is reliable experience accumulation. Claims of improved capability require uncontaminated future-task evaluation. See the evaluation protocol for baselines, ablations, and falsification criteria.

## License

MIT. See [LICENSE](LICENSE).
