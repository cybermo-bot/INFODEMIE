import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

// Expected menus mirror apps/api/pnsi/authz/permissions.py (backend unit tests
// check the same matrix; here we check the browser shows exactly that).
const MENUS: Record<string, string[]> = {
  analyste: ["veille", "signaux", "signaux_sanitaires", "dossiers", "narratifs", "reponses",
             "alertes", "actions", "preuves", "rapports", "sources"],
  referent_scientifique: ["signaux", "signaux_sanitaires", "dossiers", "narratifs", "reponses",
                          "preuves", "rapports"],
  redacteur: ["dossiers", "reponses", "actions", "preuves"],
  reviseur_linguistique: ["dossiers", "reponses"],
  approbateur: ["dossiers", "reponses", "approbations", "alertes", "actions", "preuves", "rapports"],
  cabinet: ["cabinet", "rapports"],
  partenaire: ["partenaires", "rapports"],
  relais_terrain: ["terrain"],
  administrateur: ["sources", "administration"],
};

for (const [role, menu] of Object.entries(MENUS)) {
  test(`${role} logs in and sees only its menu`, async ({ page }) => {
    await loginAs(page, role);
    const keys = await page.locator("[data-nav-key]").evaluateAll((els) =>
      els.map((el) => el.getAttribute("data-nav-key")),
    );
    expect(keys).toEqual(menu);
  });
}

test("a section outside the role's menu is refused in the UI", async ({ page }) => {
  await loginAs(page, "cabinet");
  await page.goto("/fr/administration");
  await expect(page.getByTestId("section-forbidden")).toBeVisible();
});

test("the API refuses a forbidden call with 403", async ({ page }) => {
  await loginAs(page, "analyste");
  const status = await page.evaluate(async () => (await fetch("/api/v1/audit-events")).status);
  expect(status).toBe(403);
});

test("Arabic mirrors the layout and keeps Latin text left-to-right", async ({ page }) => {
  // After login the saved language (French) wins; switch the way a user would.
  await loginAs(page, "analyste");
  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page).toHaveURL(/\/ar(\/|$)/);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");

  const nav = await page.getByRole("navigation", { name: "التنقل الرئيسي" }).boundingBox();
  const main = await page.locator("main").boundingBox();
  expect(nav && main && nav.x > main.x).toBe(true);

  // dir="auto" resolves to ltr for a Latin email inside the RTL page.
  const email = page.getByTestId("user-email").locator("bdi");
  expect(await email.evaluate((el) => el.matches(":dir(ltr)"))).toBe(true);

  await page.getByRole("button", { name: "Français" }).click();
  await expect(page).toHaveURL(/\/fr(\/|$)/);
});

test("the saved language opens after the next login", async ({ page }) => {
  await loginAs(page, "partenaire");
  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page).toHaveURL(/\/ar(\/|$)/);
  await page.context().clearCookies();
  await loginAs(page, "partenaire", "fr");
  await expect(page).toHaveURL(/\/ar(\/|$)/);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page.getByRole("button", { name: "Français" }).click();
  await expect(page).toHaveURL(/\/fr(\/|$)/);
});

test("French layout is left-to-right with navigation on the left", async ({ page }) => {
  await loginAs(page, "analyste", "fr");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  const nav = await page.getByRole("navigation", { name: "Navigation principale" }).boundingBox();
  const main = await page.locator("main").boundingBox();
  expect(nav && main && nav.x < main.x).toBe(true);
});

test("switching language is saved on the account", async ({ page }) => {
  await loginAs(page, "redacteur", "fr");
  await page.getByRole("button", { name: "English" }).click();
  await expect(page).toHaveURL(/\/en(\/|$)/);
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  const locale = await page.evaluate(async () => (await (await fetch("/api/v1/me")).json()).locale);
  expect(locale).toBe("en");
  // Put it back so the next run starts in French.
  await page.getByRole("button", { name: "Français" }).click();
  await expect(page).toHaveURL(/\/fr(\/|$)/);
});
