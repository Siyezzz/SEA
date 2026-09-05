# Related systems and adoption decisions

Reviewed on 2026-09-05. This is a targeted engineering review, not an exhaustive survey or a replication. We inspected primary paper pages, project READMEs, and selected implementation files. Repository links identify the projects observed on this date; upstream branches can change. No upstream code is vendored or executed by this change. SEA's new selection primitives are independent implementations of the documented formulas, not reproductions of entire systems.

## The closest precedents for recursive evolution

The [Godel Machine](https://people.idsia.ch/~juergen/goedelmachine.html), introduced in 2003, explicitly includes its proof searcher among the code that may be rewritten. This is the clearest theoretical precedent for treating the improvement mechanism itself as evolvable. Its optimality claims depend on provability within the formal setup; an LLM proposing a plausible patch does not satisfy that condition.

[Godel Agent](https://arxiv.org/abs/2410.04444) moves toward LLM-driven changes to an agent's own logic. [Hyperagents](https://arxiv.org/abs/2603.19461) explicitly studies an editable task agent and meta-level improvement procedure. These are close relatives of SEA's principle, so that principle should be presented as a commitment with precedents, not a novel invention.

## GitHub comparison

| System | What it contributes | What SEA should learn | Adoption status |
|---|---|---|---|
| [Godel Agent](https://github.com/Arvid-pku/Godel_Agent) | LLM-directed changes to agent logic; task-specific evaluation adapters | High-level goals with inspectable self-modification; environment feedback still needs implementation | Architectural reference; no full integration |
| [HyperAgents](https://github.com/facebookresearch/HyperAgents) | Editable task/meta agents and generation archive | Permit proposals against the learning procedure itself; preserve revision lineage | Arbitrary component identifiers supported by the offline comparison interface; successor execution pending |
| [DGM](https://github.com/jennyzzt/dgm) | Archive-based code evolution and empirical evaluation | Retain alternatives and evaluate candidates in stages | Frontier comparison implemented; persistent program archive and staged execution pending |
| [GEPA](https://github.com/gepa-ai/gepa) | Reflection over execution traces and Pareto-aware candidate search | Preserve complementary candidates; use rich feedback to propose targeted changes | Generic objective-space Pareto filter implemented; not GEPA's per-instance selection or reflection algorithm |
| [OpenEvolve](https://github.com/algorithmicsuperintelligence/openevolve) | Evolutionary program search, diversity and cascade evaluation | Cheap checks before expensive evaluation; balance exploitation with alternatives | Design reference; no external runtime dependency |
| [AgentEvolver](https://github.com/modelscope/AgentEvolver) | Self-questioning, experience-guided navigation, credit assignment and training | Generate learnable tasks and distinguish step contributions | Deferred until real rollouts and training infrastructure exist |
| [Alita](https://github.com/CharlesQ9/Alita) | Minimal predefined capabilities and on-demand reusable tools | Create a tool when an observed capability gap justifies it | Design reference; automatic tool generation pending |
| [ACE](https://github.com/ace-agent/ace) | Incremental curation of contextual playbooks | Update local lessons instead of repeatedly rewriting the entire history | Existing core guidance; automatic curator pending |
| [MemRL](https://github.com/MemTensor/MemRL) | Relevance retrieval followed by feedback-learned utility | Distinguish semantic similarity from actual usefulness | Existing lexical/utility baseline only; not a full MemRL implementation |

Selected code inspection: HyperAgents' [parent selector](https://github.com/facebookresearch/HyperAgents/blob/main/select_next_parent.py) reads archived generations, filters parent eligibility, and aggregates domain scores. Its [meta agent entry](https://github.com/facebookresearch/HyperAgents/blob/main/meta_agent.py) delegates improvement through an agent interface. DGM's [outer loop](https://github.com/jennyzzt/dgm/blob/main/DGM_outer.py) exposes archive retention and parent-selection alternatives plus staged-evaluation logic. These observations motivate separating candidate eligibility, search allocation, and activation. SEA does not copy their exact policies.

## Principles to adopt

1. All SEA components can be proposed as mutation targets, including the runner and evaluator. A fixed contract applies to one experiment, not to all future system design.
2. Keep proposals, observed evidence, and promotion decisions distinct. A reflection can suggest a change but cannot certify its own outcome.
3. Maintain alternatives with different strengths. A single scalar winner can discard a cheaper or more general strategy worth exploring later.
4. Budget learning itself. Reflection, candidate generation, retrieval, and failed tests count toward costs.
5. Prefer learning progress over surprise alone. See [Learning Progress Monitoring](https://arxiv.org/abs/2509.25438); random noise can remain surprising without becoming learnable.
6. Preserve raw evidence and local updates. Context compression must be judged by downstream decisions and recoverability.

## Methods deliberately not stacked into this prototype

- Full reinforcement learning and attribution-based training: [AgentEvolver](https://arxiv.org/abs/2511.10395) requires trajectories, task environments, and a training stack that SEA does not yet have.
- Proof-search self-rewrites: the Godel Machine supplies a useful principle, but ordinary software tasks rarely offer the axioms and tractable proofs required for its guarantees.
- MAP-Elites and island populations: [MAP-Elites](https://arxiv.org/abs/1504.04909) preserves high-performing solutions in behavior-defined niches. Meaningful descriptors and enough evaluated candidates are prerequisites; adding empty grids would not help SEA today.
- Full GEPA reflection and recombination: [GEPA](https://arxiv.org/abs/2507.19457) is a promising adapter once a model and evaluator are connected. A generic Pareto filter alone does not reproduce GEPA.
- Automatic semantic memory compression and embeddings: require a measured retrieval baseline, a model adapter, and token/cost accounting. Current byte packing remains an explicit baseline.

Adopt a method when an ablation shows a benefit under the same total budget. More algorithms are not evidence of a better learner. The initial selectors in this repository are themselves replaceable candidates, subject to the same independent comparison process.

## Next integration milestone

Connect one host model and one reproducible task environment. Capture actual paired outcomes, retain source revisions and evidence artifacts, and feed them into `evolution.py`. Add candidate execution and controlled handover only with the host's existing permissions. Separately calibrate evaluator changes against independent outcomes before using them to judge task-agent changes. The current release provides offline comparison, not an autonomous recursive agent.
