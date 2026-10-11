import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Bidi } from "@/components/Bidi";
import { directionOf, isAppLocale, locales } from "@/i18n/locales";
import { formatDateTime } from "@/lib/format";
import { findSection } from "@/lib/sections";

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

describe("direction", () => {
  it("Arabic is right-to-left, the others left-to-right", () => {
    expect(directionOf("ar")).toBe("rtl");
    expect(directionOf("fr")).toBe("ltr");
    expect(directionOf("en")).toBe("ltr");
  });

  it("offers exactly fr, ar, en with Italian disabled", () => {
    expect([...locales]).toEqual(["fr", "ar", "en"]);
    expect(isAppLocale("it")).toBe(false);
  });

  it("isolates embedded runs so Latin text stays LTR inside Arabic", () => {
    expect(renderToStaticMarkup(<Bidi>analyste@pnsi.local</Bidi>)).toBe(
      '<bdi dir="auto">analyste@pnsi.local</bdi>',
    );
  });

  const physical =
    /(?<![\w-])(?:-?m[lr]|p[lr]|left|right|border-[lr]|rounded-[lr]|text-left|text-right|float-left|float-right)-?[\w[\]./]*(?=["'\s`])/;

  it("detects physical direction utilities", () => {
    for (const bad of ["ml-4", "pr-2", "-mr-1", "text-right", "right-0", "border-l", "rounded-r-md"]) {
      expect(physical.test(`${bad} `), bad).toBe(true);
    }
    for (const ok of ["ms-4", "pe-2", "text-end", "end-0", "border-e", "flex", "rounded-md", "p-4"]) {
      expect(physical.test(`${ok} `), ok).toBe(false);
    }
  });

  it("uses logical Tailwind utilities only, so layouts mirror in Arabic", () => {
    const offenders: string[] = [];
    for (const path of files(resolve(__dirname, "../../src"))) {
      if (!/\.(tsx?|css)$/.test(path)) continue;
      for (const match of readFileSync(path, "utf8").matchAll(/className=["{`]([^"`}]*)/g)) {
        for (const cls of match[1]!.split(/\s+/)) {
          if (physical.test(`${cls} `)) offenders.push(`${path}: ${cls}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("dates", () => {
  it("shows UTC timestamps in Africa/Tunis time", () => {
    // 23:30 UTC on 11 October is 00:30 on 12 October in Tunis (UTC+1).
    const fr = formatDateTime("2026-10-11T23:30:00Z", "fr");
    expect(fr).toContain("12");
    expect(fr).toContain("00:30");
  });

  it("uses Western digits in Arabic, as written in Tunisia", () => {
    const ar = formatDateTime("2026-10-11T23:30:00Z", "ar");
    expect(ar).toMatch(/00:30/);
    expect(ar).not.toMatch(/[٠-٩]/);
  });
});

describe("sections", () => {
  const nav = [
    { key: "signaux", path: "/signaux", stage: 2 },
    { key: "signaux_sanitaires", path: "/signaux-sanitaires", stage: 6 },
  ];

  it("finds allowed sections by URL segment", () => {
    expect(findSection(nav, "signaux-sanitaires")?.key).toBe("signaux_sanitaires");
  });

  it("returns nothing for sections outside the user's menu", () => {
    expect(findSection(nav, "administration")).toBeUndefined();
  });
});
