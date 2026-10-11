import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import ar from "../../messages/ar.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";

type Tree = { [key: string]: string | Tree };
const catalogues: Record<string, Tree> = { fr, ar, en };
const repo = resolve(__dirname, "../../../..");

function flatten(tree: Tree, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") out[path] = value;
    else Object.assign(out, flatten(value, path));
  }
  return out;
}

const flat = Object.fromEntries(Object.entries(catalogues).map(([k, v]) => [k, flatten(v)]));
const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("message catalogues", () => {
  it("have the same keys in fr, ar and en", () => {
    const keys = Object.keys(flat.fr!).sort();
    expect(Object.keys(flat.ar!).sort()).toEqual(keys);
    expect(Object.keys(flat.en!).sort()).toEqual(keys);
  });

  it("have no empty strings and the same placeholders", () => {
    for (const [key, value] of Object.entries(flat.fr!)) {
      for (const locale of ["ar", "en"]) {
        const other = flat[locale]![key]!;
        expect(other.trim(), `${locale}:${key}`).not.toBe("");
        expect(placeholders(other), `${locale}:${key}`).toEqual(placeholders(value));
      }
    }
  });

  it("contain no em dash (writing rule 11)", () => {
    for (const [locale, entries] of Object.entries(flat)) {
      for (const [key, value] of Object.entries(entries)) {
        expect(value.includes("\u2014"), `${locale}:${key}`).toBe(false);
      }
    }
  });

  it("Arabic interface strings are written in Arabic script", () => {
    const latinAllowed = new Set(["app.short", "language.fr", "language.en"]);
    for (const [key, value] of Object.entries(flat.ar!)) {
      if (latinAllowed.has(key)) continue;
      expect(/[؀-ۿ]/.test(value), key).toBe(true);
    }
  });

  it("label every menu item the API can return", () => {
    const source = readFileSync(resolve(repo, "apps/api/pnsi/authz/permissions.py"), "utf8");
    const navKeys = [...source.matchAll(/NavItem\("(\w+)"/g)].map((m) => m[1]!);
    expect(navKeys.length).toBeGreaterThan(10);
    for (const key of navKeys) expect(flat.fr![`nav.${key}`], key).toBeDefined();
  });

  it("label every role in the API schema", () => {
    const schema = JSON.parse(readFileSync(resolve(repo, "packages/api-client/openapi.json"), "utf8"));
    const roles: string[] = schema.components.schemas.Role.enum;
    expect(roles).toHaveLength(9);
    for (const role of roles) expect(flat.fr![`roles.${role}`], role).toBeDefined();
  });
});
