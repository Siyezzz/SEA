# First-use acknowledgement and community participation

SEA recommends **community-contribute** during onboarding: learn from relevant shared experience and give back reviewed, reusable, non-private methods and outcomes. A recommendation or preselected option is not consent. Downloading or installing the code does not acknowledge anything on the user's behalf.

The standard MCP entry point now blocks memory and comparison tools until an explicit choice is recorded for the current version of the notice. `get_usage_status` remains available to explain the scope, saved choice, and real connection status. The host presents that notice, then uses `acknowledge_usage` only after the user's explicit choice. Version, mode, acknowledgement time, and source are stored locally. Reuse valid consent; do not repeatedly interrupt ordinary work. Changes to mode require the user's request.

| Mode | Intended community behavior | Local learning |
|---|---|---|
| community-contribute (recommended) | Selective lookup and reviewed non-private contributions | Available |
| community-read | Selective lookup without contribution | Available |
| local-only | No community exchange | Available |

All community behavior in this table is planned. This release stores the user's choice but has **no community upload, search, or telemetry client**. `sharing_active` is always false. When a real service exists, disclose its recipient, exact fields, retention, and reuse terms and obtain a new acknowledgement before transmission. Recording a future preference does not authorize an unspecified destination.

Eligible contributions should be general methods, synthetic examples, non-private evaluation summaries, and counterexamples. Exclude raw conversations, private files/source code, credentials, identifiers, local preferences, private project names/paths, and raw trajectories. Do not serialize the whole memory database into an upload. Sensitive-data detection alone cannot establish that an artifact is non-private: inspect its contents and provenance. A future bounded automatic policy must define what qualifies for release and what still needs review.

The feedback loop is: try a method, validate it, contribute a reviewed generalization, retrieve relevant community alternatives, test locally, and give back observed corrections. Sharing can improve access to experience, but cannot guarantee faster learning for every task. Local-only users retain their model's pretraining and their own history; saying they start from zero would be false. Public source code and already downloaded public knowledge also remain available. There is no artificial memory reset or skill penalty for declining.

The notice is an operational acknowledgement, not a claim of legal compliance or a final public contribution license. The repository retains its MIT code license. Before public service launch, settle content reuse/withdrawal terms and implement actual recipient controls. Publicly downloaded copies cannot be guaranteed erased later.

The gate covers the unmodified MCP entry point. A local open-source library cannot force every downloader, fork, or custom client to show a UI or truthfully report consent. Production service endpoints must independently verify an authenticated account's current acknowledgement before accepting contributions. The development library and synthetic demos are not a consent-enforcement boundary. Host/model data handling remains separate from SEA community sharing.
