import { env } from "cloudflare:workers";
import { applyD1Migrations } from "cloudflare:test";
import { beforeAll, describe, expect, it } from "vitest";
import worker from "./index";

type Migration = { name: string; queries: string[] };
const encoder = new TextEncoder();

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonical(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function hex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function sha256(value: string): Promise<string> {
  return hex(await crypto.subtle.digest("SHA-256", encoder.encode(value)));
}

async function signature(secret: string, timestamp: string, nonce: string, method: string, path: string, body: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const message = `${timestamp}\n${nonce}\n${method}\n${path}\n${await sha256(body)}`;
  return hex(await crypto.subtle.sign("HMAC", key, encoder.encode(message)));
}

beforeAll(async () => {
  const migrations = (env as Env & { TEST_MIGRATIONS: Migration[] }).TEST_MIGRATIONS;
  await applyD1Migrations(env.DB, migrations);
});

describe("SEA community registry", () => {
  it("publishes and retrieves a signed privacy-screened package", async () => {
    const runtimeEnv = env as Env & { ADMIN_TOKEN: string; CLIENT_KEY_SEED: string };
    const policyResponse = await worker.fetch(new Request("https://sea.test/v1/policy"), runtimeEnv);
    const policy = await policyResponse.json<{ version: string }>();
    expect(policy.version).toBe("2026-09-07.1");

    const enrollment = await worker.fetch(new Request("https://sea.test/v1/admin/enroll", {
      method: "POST",
      headers: { Authorization: "Bearer synthetic-admin-token-for-tests", "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: "test-client", policy_version: policy.version, can_contribute: true }),
    }), runtimeEnv);
    expect(enrollment.status).toBe(201);
    const credentials = await enrollment.json<{ client_secret: string }>();

    const unsigned = {
      schema: "sea-wisdom/1.0", revision: 1, parent_ids: [], problem: "Parse CSV safely",
      conditions: ["Unknown encoding"], method: "Detect encoding before parsing",
      counterexamples: ["Known UTF-8 fixture"], outcomes: { successes: 3, failures: 0, mean_reward: 1 },
      compatibility: { models: [], tools: ["python"], environments: ["test"] },
      producer: { component: "community-sync-policy", revision: "community-sync-policy/1.0", policy_version: policy.version },
      created_at: "2026-09-07T00:00:00Z",
    };
    const wisdomPackage = { ...unsigned, package_id: await sha256(canonical(unsigned)) };
    const body = canonical(wisdomPackage);
    const path = "/v1/packages";
    const timestamp = String(Math.floor(Date.now() / 1000));
    const nonce = "a".repeat(32);
    const published = await worker.fetch(new Request(`https://sea.test${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json", "X-SEA-Client": "test-client", "X-SEA-Timestamp": timestamp,
        "X-SEA-Nonce": nonce, "X-SEA-Policy-Version": policy.version,
        "X-SEA-Signature": await signature(credentials.client_secret, timestamp, nonce, "POST", path, body),
      },
      body,
    }), runtimeEnv);
    expect(published.status).toBe(201);
    expect(await published.json()).toMatchObject({ package_id: wisdomPackage.package_id, state: "candidate" });

    const replay = await worker.fetch(new Request(`https://sea.test${path}`, {
      method: "POST", headers: {
        "Content-Type": "application/json", "X-SEA-Client": "test-client", "X-SEA-Timestamp": timestamp,
        "X-SEA-Nonce": nonce, "X-SEA-Policy-Version": policy.version,
        "X-SEA-Signature": await signature(credentials.client_secret, timestamp, nonce, "POST", path, body),
      }, body,
    }), runtimeEnv);
    expect(replay.status).toBe(401);
  });
});
