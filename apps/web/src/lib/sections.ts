import type { Me } from "@pnsi/api-client";

export type NavItem = Me["nav"][number];

// Match a URL segment (e.g. "signaux-sanitaires") to a menu item the user may see.
export function findSection(nav: readonly NavItem[], segment: string): NavItem | undefined {
  return nav.find((item) => item.path === `/${segment}`);
}
