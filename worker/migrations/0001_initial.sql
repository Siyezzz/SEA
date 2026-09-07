CREATE TABLE clients (
  id TEXT PRIMARY KEY,
  policy_version TEXT NOT NULL,
  can_contribute INTEGER NOT NULL CHECK (can_contribute IN (0, 1)),
  created_at TEXT NOT NULL
);

CREATE TABLE nonces (
  client TEXT NOT NULL,
  nonce TEXT NOT NULL,
  used_at INTEGER NOT NULL,
  PRIMARY KEY (client, nonce)
);

CREATE TABLE packages (
  id TEXT PRIMARY KEY,
  revision INTEGER NOT NULL,
  parent_ids TEXT NOT NULL,
  body TEXT NOT NULL,
  search_text TEXT NOT NULL,
  author TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('candidate', 'active', 'withdrawn')),
  created_at TEXT NOT NULL
);

CREATE TABLE community_feedback (
  package TEXT NOT NULL,
  client TEXT NOT NULL,
  task TEXT NOT NULL,
  reward REAL NOT NULL CHECK (reward >= 0 AND reward <= 1),
  evidence_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (package, client, task)
);

CREATE TABLE component_versions (
  component TEXT NOT NULL,
  revision TEXT NOT NULL,
  predecessor TEXT,
  artifact_digest TEXT NOT NULL,
  evaluation_contract TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('candidate', 'active', 'predecessor', 'rejected')),
  created_at TEXT NOT NULL,
  PRIMARY KEY (component, revision)
);

CREATE INDEX packages_state_created ON packages(state, created_at);
CREATE INDEX packages_search ON packages(search_text);
CREATE INDEX feedback_package ON community_feedback(package);
CREATE INDEX nonces_used_at ON nonces(used_at);

INSERT INTO component_versions VALUES
  ('community-registry', 'cloudflare-registry/1.0', NULL, 'source:worker/index.ts',
   'bootstrap:requires-successor-evaluation', 'active', CURRENT_TIMESTAMP),
  ('registry-ranking', 'lexical-ranking/1.0', NULL, 'source:worker/index.ts',
   'bootstrap:requires-successor-evaluation', 'active', CURRENT_TIMESTAMP),
  ('registry-privacy-filter', 'deterministic-filter/1.0', NULL, 'source:worker/index.ts',
   'bootstrap:requires-successor-calibration', 'active', CURRENT_TIMESTAMP);
