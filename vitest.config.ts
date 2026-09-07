import { cloudflareTest, readD1Migrations } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig(async () => ({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: {
          ADMIN_TOKEN: "synthetic-admin-token-for-tests",
          CLIENT_KEY_SEED: "synthetic-client-key-seed-for-tests",
          TEST_MIGRATIONS: await readD1Migrations("./worker/migrations"),
        },
      },
    }),
  ],
}));
