import { readCookie } from "@pnsi/api-client";
import { describe, expect, it } from "vitest";

describe("api client", () => {
  it("reads the CSRF cookie among others", () => {
    expect(readCookie("pnsi_csrf", "a=1; pnsi_csrf=tok%3Den; b=2")).toBe("tok=en");
    expect(readCookie("pnsi_csrf", "a=1")).toBeUndefined();
  });
});
