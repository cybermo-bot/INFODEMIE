import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { Page } from "@playwright/test";

const credentialsFile =
  process.env.SEED_CREDENTIALS ?? resolve(__dirname, "../../../../data/seed-credentials.txt");

export function seedPassword(email: string): string {
  for (const line of readFileSync(credentialsFile, "utf8").split("\n")) {
    const [user, password] = line.split("\t");
    if (user === email && password) return password;
  }
  throw new Error(`${email} not found in ${credentialsFile}: run make seed`);
}

export function seedEmail(role: string): string {
  return `${role.replaceAll("_", ".")}@pnsi.local`;
}

export async function loginAs(page: Page, role: string, locale = "fr") {
  const email = seedEmail(role);
  await page.goto(`/${locale}/login`);
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(seedPassword(email));
  await page.locator('button[type="submit"]').click();
  await page.getByTestId("main-nav").waitFor();
}
