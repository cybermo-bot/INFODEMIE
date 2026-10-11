import { defineConfig, devices } from "@playwright/test";

// Runs against a running stack (`make dev` after `make seed`). Credentials are
// read from data/seed-credentials.txt, written by the seed command.
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } } },
  ],
});
