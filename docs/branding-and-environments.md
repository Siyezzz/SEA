# Brand and execution environment

## Wave identity

SEA uses an original minimal sea-surface mark: blue and cyan ripples with a small warm-gold reflection on deep ocean blue. `assets/sea-icon.svg` is the scalable source export, `assets/sea-icon.png` is the Codex plugin image, and `assets/sea-social.png` is a repository banner/social-card asset. The mark is embedded in the GitHub README. The social-card file does not itself configure GitHub's repository social-preview setting. `scripts/build_brand.py` regenerates the images using Pillow as a build-only dependency.

The desired instance progression is **drop → lake → sea → wave**. Keep this as a future per-instance profile visualization. Codex's plugin manifest currently supplies static image paths; the integration has no verified mechanism to update its displayed icon per user's learning state. The current plugin and GitHub therefore use the requested wave fallback. No badge claims a level of intelligence.

When a profile surface is implemented, base its progression on retained lessons and independently observed transfer, with visible evidence. Do not use token spending, chat count, or willingness to share as a proxy for intelligence. Regression should be representable, and no backend or capability milestone is implied by a decorative stage.

## Local versus remote Codex execution

Decision on 2026-09-06: keep SEA development and the owner instance local for now. The repository is already backed by GitHub; the installed MCP runtime and persistent database live on the user's computer. A remote execution environment does not implement community exchange or synchronize private memory automatically. No additional host or cloud environment was provisioned.

Use remote execution when an always-on host, another operating system, isolated cloud tasks, or team infrastructure becomes useful. For SSH, add and verify a trusted host, install Codex and SEA's dependencies there, then use Settings > Connections to select its project folder. Install/configure the MCP service on that host with a deliberate local database path. For cloud development, connect the GitHub repository and install `requirements-mcp.txt` in the environment setup; use test databases instead of copying an owner's private database.

Sources: [Codex remote connections](https://learn.chatgpt.com/docs/remote-connections) and [cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment). These are execution choices, independent of the planned shared experience service.
