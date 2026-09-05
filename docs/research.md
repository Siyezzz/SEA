# From instructions to learn to testable self-evolution

Research date: 2026-09-05. These notes selectively examine public papers and their methods and limitations. They are not a systematic review or an independent replication. Some 2026 work is preliminary. Engineering proposals below are distinguished from published findings, and scores from different benchmarks are not compared.

## 1. What the human-learning analogy captures

The simplified sequence hunger, crying, and receiving milk illustrates state, action, feedback, and retention. A single sequence does not establish causality, and infant behavior cannot be reduced to a conscious rule learned from one event. For agents, task success must be distinguished from evidence that a particular strategy caused that success. Rewarding every retrieved memory after a successful task can reinforce irrelevant advice.

Talking to a stranger does not require a person-specific skill file because general abilities can be composed for a new situation. Pretraining similarly gives agents broad priors. A deployed agent can devise a new approach; the hard questions are whether the discovery persists, is retrieved later, transfers appropriately, and is corrected by counterexamples.

An instruction to try harder may influence behavior, but it supplies neither trustworthy rewards nor persistence nor independent evaluation. It may even reward the appearance of effort. A better core protocol asks for falsifiable hypotheses, bounded experiments, observed outcomes, and retention of useful changes.

## 2. Relevant research

| Paper | Mechanism and relevance | Boundary |
|---|---|---|
| [Reflexion, 2023](https://arxiv.org/abs/2303.11366) | Stores language reflections derived from feedback in episodic memory | Reflection is not a weight update or a guarantee of long-term transfer |
| [Voyager, 2023](https://arxiv.org/abs/2305.16291) | Automatic curriculum, feedback iteration, and executable skill library | Minecraft exploration does not establish general desktop reliability |
| [A-MEM, 2025](https://arxiv.org/abs/2502.12110) | Dynamically organizes, links, and updates memories | Richer links do not establish causal strategy effectiveness |
| [Mem0, 2025](https://arxiv.org/abs/2504.19413) | Extracts, consolidates, and retrieves salient information | Conversation recall and autonomous capability growth are different outcomes |
| [Darwin Godel Machine, 2025](https://arxiv.org/abs/2505.22954) | Modifies agent programs, evaluates variants, and retains a diverse archive | Evaluation coverage, compute costs, and benchmark adaptation limit conclusions |
| [ACE, 2025](https://arxiv.org/html/2510.04618v1) | Evolves context through generation, reflection, and incremental curation | Avoiding destructive rewriting still leaves context-budget management necessary |
| [Recursive Language Models, 2025-12](https://arxiv.org/html/2512.24601v1) | Keeps long input in an external environment for programmatic and recursive inspection | Long-input processing is not infinite attention or proof of lifelong learning |
| [MemRL, 2026-01](https://arxiv.org/html/2601.03192v1) | Semantic recall followed by selection using feedback-learned utility | Learning is external to frozen weights; attribution and task distribution still matter |
| [Hyperagents, 2026-03](https://arxiv.org/html/2603.19461v1) | Makes the task agent and its improvement procedure part of an editable program | Experiments do not prove unconditional or unbounded acceleration |
| [Dynamic graph transformation survey, 2026-08](https://arxiv.org/abs/2608.18104) | Frames evolving agents as changing graph structures | A taxonomy provides perspective, not experimental evidence for SEA |

The immediate opportunity is to combine language experience, incremental curation, utility feedback, and validation archives. Updating model weights need not be the starting point.

## 3. Growing memory without growing every prompt

Long-term human memory is not identical to everything simultaneously held in working memory. This is a functional analogy, not an equivalence between neuroscience and databases.

Model weights, external memory, and active context should also be separated. Weights supply broad priors; storage retains experiences; active context contains information needed now. RLMs explore keeping input outside the model window and inspecting it on demand, but inspection and subcalls still have costs. [RLM](https://arxiv.org/html/2512.24601v1)

For conventional dense attention, longer inputs increase prefill work. With KV caching, each generated step still processes existing keys and values, affecting memory and bandwidth. Actual latency depends on model architecture, caching, and implementation; not all inference can be described as quadratic. See [Attention Is All You Need](https://arxiv.org/abs/1706.03762) for standard attention complexity. External retrieval also has nonzero scaling costs.

The useful compression objective is preserving information needed for the next decision under a fixed budget. A broad summary can lose exceptions, exact values, and unresolved questions. ACE's discussion of information loss during repeated rewriting motivates local updates. [ACE](https://arxiv.org/html/2510.04618v1)

Keep four types of object: task state (goals, constraints, next steps), original evidence (read on demand), conditional lessons (conditions, actions, outcomes, counterexamples), and executable procedures (created only when reuse justifies them). Archiving removes an object from the default working set without erasing its history. Keep the core skill small and retrieve other material as needed.

## 4. Three testable combinations

### A. Traceable promotion rather than self-declared mastery

Experience becomes a candidate hypothesis, then a project strategy, a transferable strategy, and possibly an executable skill. Each transition needs evidence and can be reversed. General research or debugging lessons can remain conditional strategies; repeated execution structure may justify a skill. A completed project's lessons leave the active set. Cross-project reuse should create a separately validated general candidate rather than silently globalizing a local convention.

The prototype implements candidates, activation, demotion, and archival. Its three-case threshold makes lifecycle behavior explicit; it is not a statistical significance test and would need calibration for real tasks.

### B. Memory value as the difference it makes

Proposed experiment: compare reproducible tasks with and without a memory. Define utility gain as quality improvement minus weighted extra cost and regression loss. Keep uncertain lessons as candidates and retain counterexamples. Randomized memory ablation can improve on crediting every memory after success, but requires controls for model randomness, budgets, and task difficulty.

This follows the utility-oriented direction of MemRL while proposing more explicit counterfactual attribution. The prototype's smoothed reward mean is not a full implementation of MemRL or a causal estimator.

### C. Recoverable decision compression

Retain original records and build views from an index to conditional lessons to evidence excerpts. A compressor should construct the state needed for the current task instead of overwriting the only history. Evaluate next-action correctness and evidence recovery, not just summary similarity.

Use preservation of goals, constraints, critical facts, open questions, and provenance as explicit checks, and future task performance as the behavioral outcome. The current prototype only packs whole records into a byte budget; automatic semantic compression and task-state compilation remain unimplemented.

## 5. Curiosity without endless busywork

Exploration should target worthwhile, learnable uncertainty. Unpredictable noise can remain surprising without yielding useful learning: the noisy-TV problem. [Original research](https://arxiv.org/abs/2102.04399)

[Learning Progress Monitoring, 2025](https://arxiv.org/abs/2509.25438) studies rewarding learning progress rather than raw prediction error. An initial engineering rule for agents is simpler: experiments should be relevant to the user's objective, cheaply testable, reversible, and affordable within the remaining budget. Stop when repeated attempts add no useful evidence. This guidance is a hypothesis, not a trained intrinsic motivation system.

## 6. What would count as progress?

Persistent adaptation is useful if memories improve subsequent tasks, old capabilities remain stable, context costs stay controlled, and gains survive a new session and transfer tests. More Markdown files, longer reflections, or higher discovery-task scores are insufficient evidence.

The next milestone is a real host integration with an independent evaluator and chronological held-out tasks. Establish experience-driven gains before pursuing automatic skill generation or self-modification of the improvement mechanism.

## 7. Recursive evolution without a permanently fixed runner

SEA's design principle is that every component may become an object of improvement: stored experience, retrieval, executable skills, the core learning protocol, the runner, scheduling, candidate generation, and evaluation methodology. An initial program must start the loop, but that does not make it permanently exempt from evolution. This is a design commitment, not a capability implemented by the current prototype.

There need not be an endless stack of separately designed meta-runners. A versioned system can propose changes to its own implementation and test a successor. The currently running version evaluates a candidate in an isolated experiment; a validated successor takes over at a controlled boundary, retaining provenance and a recoverable predecessor. Runner changes must also preserve task state, budgets, and pending work across that boundary.

Evaluation methods can evolve too. During a particular comparison, preserve the evaluation contract so that the candidate cannot win merely by redefining success. Proposed evaluator changes require separate calibration against independent outcomes and fresh held-out tasks. Evaluator quality and task-agent quality are distinct claims. Independence is a relationship between a proposal and its evidence, not a claim that one software component must stay unchanged forever.

The user-defined objective and execution permissions remain authoritative. An architectural ability to propose a change is not authorization to bypass settings, delete user files, or expand access. Within those boundaries, no SEA implementation component is categorically excluded from improvement. Progress, including improvements to the learning process itself, remains an empirical claim that may fail.
