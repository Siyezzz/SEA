# First-use acknowledgement and community participation

SEA recommends **community-contribute** during onboarding: learn from relevant shared experience and give back reviewed, reusable, non-private methods and outcomes. A recommendation or preselected option is not consent. Downloading or installing the code does not acknowledge anything on the user's behalf.

The standard MCP entry point now blocks memory and comparison tools until an explicit choice is recorded for the current version of the notice. `get_usage_status` remains available to explain the scope, saved choice, and real connection status. The host presents that notice, then uses `acknowledge_usage` only after the user's explicit choice. Version, mode, acknowledgement time, and source are stored locally. Reuse valid consent; do not repeatedly interrupt ordinary work. Changes to mode require the user's request.

| Mode | Community behavior | Local learning |
|---|---|---|
| community-contribute (recommended) | Selective lookup and reviewed non-private contributions | Available |
| community-read | Selective lookup without contribution | Available |
| local-only | No community exchange | Available |

The community client is implemented. It becomes active only when a registry URL, client ID, client secret, and a current acknowledgement are all present. `get_usage_status` exposes the configured recipient and `sharing_active`; it never treats installation as acceptance. The client has no ambient telemetry and does not upload the local database. A package is built only from one active lesson, placed in a local outbox, and transmitted only when `sync_contributions` runs.

Eligible contributions are general methods, synthetic examples, aggregate non-private outcomes, applicability conditions, compatibility metadata, and counterexamples. The registered schema rejects extra fields. Deterministic screens reject common credentials, email addresses, private paths, private keys, raw conversations, source code, preferences, project names, and raw traces before queueing and again at the registry. Sensitive-data detection cannot guarantee anonymization, so the host must inspect the abstraction and provenance before contribution.

The feedback loop is: try a method, validate it, contribute a reviewed generalization, retrieve relevant community alternatives, test locally, and give back observed corrections. Sharing can improve access to experience, but cannot guarantee faster learning for every task. Local-only users retain their model's pretraining and their own history; saying they start from zero would be false. Public source code and already downloaded public knowledge also remain available. There is no artificial memory reset or skill penalty for declining.

The current notice states that accepted packages and aggregate feedback remain until a future supported withdrawal operation or operator removal. Packages may be searched, tested, revised, and redistributed to authenticated SEA clients under the repository license and service policy. Publicly downloaded copies cannot be guaranteed erased later. The notice is an operational acknowledgement, not a claim of legal compliance.

The gate covers the unmodified MCP entry point. A local open-source library cannot force every downloader, fork, or custom client to show a UI or truthfully report consent. The registry therefore accepts only enrolled clients tied to the current service-policy version and an explicit contribution capability. Host/model data handling remains separate from SEA community sharing.
