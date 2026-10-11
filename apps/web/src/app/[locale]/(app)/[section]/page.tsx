"use client";

import { useTranslations } from "next-intl";
import { use } from "react";

import { AppShell } from "@/components/AppShell";
import { findSection } from "@/lib/sections";

// Placeholder for screens delivered in later stages. The menu only links to
// sections the user's roles allow; the backend enforces the same rule.
export default function SectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = use(params);
  const t = useTranslations();
  return (
    <AppShell>
      {(me) => {
        const item = findSection(me.nav, section);
        if (!item) {
          return (
            <p role="alert" data-testid="section-forbidden">
              {t("placeholder.forbidden")}
            </p>
          );
        }
        return (
          <div className="space-y-2">
            <h1 className="text-xl font-semibold">
              {t(`nav.${item.key}` as Parameters<typeof t>[0])}
            </h1>
            <p>{t("placeholder.plannedAt", { stage: item.stage })}</p>
          </div>
        );
      }}
    </AppShell>
  );
}
