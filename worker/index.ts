const MAX_BODY_BYTES = 256_000;
const PACKAGE_SCHEMA = "sea-wisdom/1.0";
const outcomeKeys = ["failures", "mean_reward", "successes"];
const compatibilityKeys = ["environments", "models", "tools"];
const producerKeys = ["component", "policy_version", "revision"];
const encoder = new TextEncoder();
const decoder = new TextDecoder();

type SecretBindings = Readonly<{ ADMIN_TOKEN: string; CLIENT_KEY_SEED: string }>;
type RuntimeEnv = Env & SecretBindings;
type JsonObject = { [key: string]: JsonValue };
type JsonValue = null | boolean | number | string | JsonValue[] | JsonObject;

const requiredPackageKeys = ["schema", "package_id", "revision", "parent_ids", "problem", "conditions",
  "method", "counterexamples", "outcomes", "compatibility", "producer", "created_at"].sort();
const forbiddenKeys = new Set(["conversation", "transcript", "raw_trace", "credentials", "user_email",
  "local_path", "project_name", "source_code", "preference"]);
const privatePatterns: ReadonlyArray<readonly [string, RegExp]> = [
  ["email", /\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b/],
  ["credential", /\b(api[_ -]?key|password|secret|token)\s*[:=]\s*\S+/i],
  ["windows_path", /\b[A-Z]:\\(?:[^\s\\]+\\)+[^\s]+/i],
  ["unix_home_path", /\/(?:home|Users)\/[^\s/]+\/[^\s]+/],
  ["private_key", /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
];

function response(value: JsonValue, status = 200): Response {
  return Response.json(value, { status, headers: { "Cache-Control": "no-store" } });
}

function canonical(value: JsonValue): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  const serialized = JSON.stringify(value);
  if (serialized === undefined) throw new Error("Non-JSON value");
  return serialized;
}

function hex(bytes: ArrayBuffer | Uint8Array): string {
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function fromHex(value: string): Uint8Array<ArrayBuffer> | null {
  if (!/^[0-9a-f]+$/.test(value) || value.length % 2 !== 0) return null;
  return new Uint8Array(value.match(/../g)?.map((pair) => Number.parseInt(pair, 16)) ?? []);
}

async function digest(value: string | Uint8Array): Promise<string> {
  const bytes = typeof value === "string" ? encoder.encode(value) : Uint8Array.from(value);
  return hex(await crypto.subtle.digest("SHA-256", bytes));
}

async function hmacBytes(secret: string, value: string): Promise<ArrayBuffer> {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return crypto.subtle.sign("HMAC", key, encoder.encode(value));
}

async function deriveClientSecret(seed: string, clientId: string): Promise<string> {
  return hex(await hmacBytes(seed, `sea-client\n${clientId}`));
}

async function verifyHmac(secret: string, value: string, signature: string): Promise<boolean> {
  const bytes = fromHex(signature);
  if (!bytes || bytes.byteLength !== 32) return false;
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  return crypto.subtle.verify("HMAC", key, bytes, encoder.encode(value));
}

async function readBody(request: Request): Promise<Uint8Array> {
  const declared = Number(request.headers.get("Content-Length") ?? 0);
  if (declared > MAX_BODY_BYTES) throw new Error("Request body is too large");
  if (!request.body) return new Uint8Array();
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY_BYTES) {
      await reader.cancel("Request body is too large");
      throw new Error("Request body is too large");
    }
    chunks.push(value);
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  return body;
}

function privacyFindings(value: JsonValue, path = "$", findings: JsonObject[] = []): JsonObject[] {
  if (Array.isArray(value)) value.forEach((item, index) => privacyFindings(item, `${path}[${index}]`, findings));
  else if (value !== null && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (forbiddenKeys.has(key.toLowerCase())) findings.push({ path: `${path}.${key}`, kind: "forbidden_field" });
      privacyFindings(item, `${path}.${key}`, findings);
    }
  } else if (typeof value === "string") {
    for (const [kind, pattern] of privatePatterns) if (pattern.test(value)) findings.push({ path, kind });
  }
  return findings;
}

function nonempty(value: unknown, max = 4000): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= max;
}

function stringList(value: unknown, maxItems = 20): value is string[] {
  return Array.isArray(value) && value.length <= maxItems && value.every((item) => nonempty(item, 1000));
}

function hasExactKeys(value: JsonObject, keys: string[]): boolean {
  return JSON.stringify(Object.keys(value).sort()) === JSON.stringify(keys);
}

async function validatePackage(value: JsonValue): Promise<JsonObject> {
  if (value === null || Array.isArray(value) || typeof value !== "object") throw new Error("Package must be an object");
  if (JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(requiredPackageKeys)) throw new Error("Invalid package fields");
  if (value.schema !== PACKAGE_SCHEMA || !nonempty(value.package_id, 64) || !/^[0-9a-f]{64}$/.test(value.package_id)) throw new Error("Invalid schema or package ID");
  if (!Number.isInteger(value.revision) || (value.revision as number) < 1) throw new Error("Invalid revision");
  if (!stringList(value.parent_ids, 8) || !nonempty(value.problem) || !stringList(value.conditions) ||
      !nonempty(value.method) || !stringList(value.counterexamples)) throw new Error("Invalid package content");
  const outcomes = value.outcomes;
  if (outcomes === null || Array.isArray(outcomes) || typeof outcomes !== "object" ||
      !hasExactKeys(outcomes, outcomeKeys) ||
      !Number.isInteger(outcomes.successes) || !Number.isInteger(outcomes.failures) ||
      (outcomes.successes as number) < 0 || (outcomes.failures as number) < 0 ||
      typeof outcomes.mean_reward !== "number" || !Number.isFinite(outcomes.mean_reward) ||
      outcomes.mean_reward < 0 || outcomes.mean_reward > 1) throw new Error("Invalid outcomes");
  const compatibility = value.compatibility;
  if (compatibility === null || Array.isArray(compatibility) || typeof compatibility !== "object" ||
      !hasExactKeys(compatibility, compatibilityKeys) ||
      !stringList(compatibility.models) || !stringList(compatibility.tools) || !stringList(compatibility.environments)) throw new Error("Invalid compatibility");
  const producer = value.producer;
  if (producer === null || Array.isArray(producer) || typeof producer !== "object" ||
      !hasExactKeys(producer, producerKeys) ||
      !nonempty(producer.component, 200) || !nonempty(producer.revision, 200) ||
      !nonempty(producer.policy_version, 200) || !nonempty(value.created_at, 100)) throw new Error("Invalid producer");
  if (privacyFindings(value).length) throw new Error("Package failed the registry privacy screen");
  const unsigned = { ...value };
  delete unsigned.package_id;
  if (await digest(canonical(unsigned)) !== value.package_id) throw new Error("Package content digest mismatch");
  return value;
}

async function authenticate(request: Request, env: RuntimeEnv, body: Uint8Array, contribution: boolean): Promise<string> {
  const clientId = request.headers.get("X-SEA-Client") ?? "";
  const client = await env.DB.prepare("SELECT policy_version, can_contribute FROM clients WHERE id=?").bind(clientId).first<{ policy_version: string; can_contribute: number }>();
  if (!client || client.policy_version !== request.headers.get("X-SEA-Policy-Version")) throw new Error("Unknown client or unaccepted service policy");
  if (contribution && client.can_contribute !== 1) throw new Error("Client cannot contribute");
  const timestamp = request.headers.get("X-SEA-Timestamp") ?? "";
  const nonce = request.headers.get("X-SEA-Nonce") ?? "";
  const seconds = Number(timestamp);
  if (!Number.isInteger(seconds) || Math.abs(Date.now() / 1000 - seconds) > 300 || !/^[0-9a-f]{32}$/.test(nonce)) throw new Error("Expired timestamp or invalid nonce");
  const url = new URL(request.url);
  const path = url.pathname + url.search;
  const message = `${timestamp}\n${nonce}\n${request.method}\n${path}\n${await digest(body)}`;
  const secret = await deriveClientSecret(env.CLIENT_KEY_SEED, clientId);
  if (!await verifyHmac(secret, message, request.headers.get("X-SEA-Signature") ?? "")) throw new Error("Invalid signature");
  try {
    await env.DB.batch([
      env.DB.prepare("INSERT INTO nonces VALUES(?,?,?)").bind(clientId, nonce, seconds),
      env.DB.prepare("DELETE FROM nonces WHERE used_at<?").bind(Math.floor(Date.now() / 1000) - 600),
    ]);
  } catch { throw new Error("Replayed request"); }
  return clientId;
}

async function enroll(request: Request, env: RuntimeEnv, body: Uint8Array): Promise<Response> {
  const token = request.headers.get("Authorization")?.replace(/^Bearer /, "") ?? "";
  const suppliedProof = await hexHmac(token, "sea-admin");
  if (!await verifyHmac(env.ADMIN_TOKEN, "sea-admin", suppliedProof)) return response({ error: "Unauthorized" }, 401);
  const value = JSON.parse(decoder.decode(body)) as JsonObject;
  if (!nonempty(value.client_id, 200) || value.policy_version !== env.SERVICE_POLICY_VERSION || typeof value.can_contribute !== "boolean") throw new Error("Invalid enrollment");
  await env.DB.prepare("INSERT INTO clients VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET policy_version=excluded.policy_version, can_contribute=excluded.can_contribute")
    .bind(value.client_id, value.policy_version, value.can_contribute ? 1 : 0, new Date().toISOString()).run();
  return response({ client_id: value.client_id, client_secret: await deriveClientSecret(env.CLIENT_KEY_SEED, value.client_id), policy_version: env.SERVICE_POLICY_VERSION }, 201);
}

async function hexHmac(secret: string, value: string): Promise<string> { return hex(await hmacBytes(secret, value)); }

async function publish(value: JsonValue, clientId: string, env: RuntimeEnv): Promise<Response> {
  const packageValue = await validatePackage(value);
  const id = packageValue.package_id as string;
  const body = canonical(packageValue);
  const existing = await env.DB.prepare("SELECT body FROM packages WHERE id=?").bind(id).first<{ body: string }>();
  if (existing) {
    if (existing.body !== body) throw new Error("Package ID collision");
    return response({ package_id: id, state: "candidate", idempotent: true });
  }
  const parents = packageValue.parent_ids as string[];
  for (const parent of parents) if (!await env.DB.prepare("SELECT id FROM packages WHERE id=?").bind(parent).first()) throw new Error("Unknown parent package");
  const searchText = `${packageValue.problem} ${(packageValue.conditions as string[]).join(" ")}`.toLowerCase();
  await env.DB.prepare("INSERT INTO packages VALUES(?,?,?,?,?,?,?,?)").bind(id, packageValue.revision,
    JSON.stringify(parents), body, searchText, clientId, "candidate", new Date().toISOString()).run();
  return response({ package_id: id, state: "candidate", idempotent: false }, 201);
}

async function search(url: URL, env: RuntimeEnv): Promise<Response> {
  const query = (url.searchParams.get("q") ?? "").trim().toLowerCase().slice(0, 500);
  const limit = Math.min(20, Math.max(1, Number.parseInt(url.searchParams.get("limit") ?? "5", 10) || 5));
  if (!query) return response([]);
  const result = await env.DB.prepare(`SELECT p.id,p.body,p.state,COUNT(f.task) feedback_count,AVG(f.reward) mean_reward
    FROM packages p LEFT JOIN community_feedback f ON f.package=p.id
    WHERE p.state IN ('candidate','active') AND p.search_text LIKE ? ESCAPE '\\'
    GROUP BY p.id ORDER BY feedback_count DESC,mean_reward DESC,p.created_at DESC LIMIT ?`)
    .bind(`%${query.replaceAll("%", "\\%").replaceAll("_", "\\_")}%`, limit).all<{ id: string; body: string; state: string; feedback_count: number; mean_reward: number | null }>();
  return response(result.results.map((row) => {
    const item = JSON.parse(row.body) as JsonObject;
    return { package_id: row.id, problem: item.problem, conditions: item.conditions, state: row.state,
      feedback_count: row.feedback_count, mean_reward: row.mean_reward };
  }));
}

async function getPackage(id: string, env: RuntimeEnv): Promise<Response> {
  const row = await env.DB.prepare("SELECT body,state FROM packages WHERE id=?").bind(id).first<{ body: string; state: string }>();
  return row ? response({ package: JSON.parse(row.body), state: row.state }) : response({ error: "Not found" }, 404);
}

async function feedback(id: string, value: JsonObject, clientId: string, env: RuntimeEnv): Promise<Response> {
  if (!await env.DB.prepare("SELECT id FROM packages WHERE id=?").bind(id).first()) return response({ error: "Not found" }, 404);
  if (!nonempty(value.task, 200) || typeof value.reward !== "number" || !Number.isFinite(value.reward) || value.reward < 0 || value.reward > 1 ||
      !nonempty(value.evidence_digest, 64) || !/^[0-9a-f]{64}$/.test(value.evidence_digest)) throw new Error("Invalid feedback");
  await env.DB.prepare("INSERT INTO community_feedback VALUES(?,?,?,?,?,?)").bind(id, clientId, value.task,
    value.reward, value.evidence_digest, new Date().toISOString()).run();
  const aggregate = await env.DB.prepare("SELECT COUNT(*) count,MIN(reward) minimum,AVG(reward) mean FROM community_feedback WHERE package=?")
    .bind(id).first<{ count: number; minimum: number; mean: number }>();
  if (!aggregate) throw new Error("Feedback aggregation failed");
  const state = aggregate.count >= 3 && aggregate.minimum >= .5 ? "active" : "candidate";
  await env.DB.prepare("UPDATE packages SET state=? WHERE id=?").bind(state, id).run();
  return response({ package_id: id, state, feedback_count: aggregate.count, mean_reward: aggregate.mean });
}

async function versions(id: string, env: RuntimeEnv): Promise<Response> {
  if (!await env.DB.prepare("SELECT id FROM packages WHERE id=?").bind(id).first()) return response({ error: "Not found" }, 404);
  const rows = await env.DB.prepare("SELECT id,revision,state,parent_ids FROM packages WHERE parent_ids LIKE ? ORDER BY created_at")
    .bind(`%${id}%`).all<{ id: string; revision: number; state: string; parent_ids: string }>();
  return response({ package_id: id, children: rows.results.filter((row) => (JSON.parse(row.parent_ids) as string[]).includes(id))
    .map((row) => ({ package_id: row.id, revision: row.revision, state: row.state })) });
}

async function components(env: RuntimeEnv): Promise<Response> {
  const rows = await env.DB.prepare("SELECT component,revision,predecessor,artifact_digest,evaluation_contract,state,created_at FROM component_versions ORDER BY component,created_at").all();
  return response({ registry_revision: env.REGISTRY_REVISION, components: rows.results as JsonValue[] });
}

export default {
  async fetch(request: Request, env: RuntimeEnv): Promise<Response> {
    const url = new URL(request.url);
    try {
      const body = await readBody(request);
      if (request.method === "GET" && url.pathname === "/health") return response({ status: "ok", revision: env.REGISTRY_REVISION });
      if (request.method === "GET" && url.pathname === "/v1/policy") return response({
        version: env.SERVICE_POLICY_VERSION,
        package_schema: PACKAGE_SCHEMA,
        maximum_body_bytes: MAX_BODY_BYTES,
        stores: ["reviewed wisdom packages", "aggregate outcome feedback", "client identifiers", "replay-prevention nonces"],
        excludes: ["raw conversations", "private files", "source code", "credentials", "personal identifiers", "raw execution traces"],
        reuse: "Packages may be searched, tested, revised, and redistributed to authenticated SEA clients.",
      });
      if (request.method === "POST" && url.pathname === "/v1/admin/enroll") return await enroll(request, env, body);
      const contribution = request.method === "POST";
      const clientId = await authenticate(request, env, body, contribution);
      if (request.method === "POST" && url.pathname === "/v1/packages") return await publish(JSON.parse(decoder.decode(body)) as JsonValue, clientId, env);
      if (request.method === "GET" && url.pathname === "/v1/search") return await search(url, env);
      if (request.method === "GET" && url.pathname === "/v1/system/components") return await components(env);
      const packageMatch = url.pathname.match(/^\/v1\/packages\/([0-9a-f]{64})(\/versions)?$/);
      if (request.method === "GET" && packageMatch) return packageMatch[2] ? await versions(packageMatch[1], env) : await getPackage(packageMatch[1], env);
      const feedbackMatch = url.pathname.match(/^\/v1\/feedback\/([0-9a-f]{64})$/);
      if (request.method === "POST" && feedbackMatch) return await feedback(feedbackMatch[1], JSON.parse(decoder.decode(body)) as JsonObject, clientId, env);
      return response({ error: "Not found" }, 404);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      const auth = /Unknown client|policy|cannot contribute|timestamp|nonce|signature|Replayed/.test(message);
      const conflict = /UNIQUE constraint failed/.test(message);
      console.error(JSON.stringify({ message: "request_failed", path: url.pathname, error: message }));
      return response({ error: auth ? message : conflict ? "Duplicate record" : message }, auth ? 401 : conflict ? 409 : 400);
    }
  },
} satisfies ExportedHandler<RuntimeEnv>;
