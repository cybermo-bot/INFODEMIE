"use client";

import { useLocale, useTranslations } from "next-intl";

import { AppShell } from "@/components/AppShell";
import { Link } from "@/i18n/navigation";
import type { Me } from "@/lib/api";

function institutionName(inst: Me["institution"], locale: string): string {
  if (locale === "ar" && inst.name_ar) return inst.name_ar;
  if (locale === "en" && inst.name_en) return inst.name_en;
  return inst.name_fr;
}

export default function HomePage() {
  const t = useTranslations();
  const locale = useLocale();
  return (
    <AppShell>
      {(me) => (
        <div className="space-y-4">
          <h1 className="text-xl font-semibold">{t("home.title")}</h1>
          <p>{t("home.intro")}</p>
          <dl className="space-y-2">
            <dt className="font-semibold">{t("shell.institution")}</dt>
            <dd>{institutionName(me.institution, locale)}</dd>
            <dt className="font-semibold">{t("shell.roles")}</dt>
            <dd>{me.roles.map((r) => t(`roles.${r}`)).join(", ")}</dd>
          </dl>
          <h2 className="font-semibold">{t("home.yourScreens")}</h2>
          <ul className="list-disc ps-6">
            {me.nav.map((item) => (
              <li key={item.key}>
                <Link href={item.path} className="underline">
                  {t(`nav.${item.key}` as Parameters<typeof t>[0])}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </AppShell>
  );
}
