"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { locales, type AppLocale } from "@/i18n/locales";
import { usePathname, useRouter } from "@/i18n/navigation";
import { api, meQueryKey, type Me } from "@/lib/api";

// Switches the interface language. When signed in, the choice is saved on the
// account so the next login opens in the same language.
export function LanguageSwitcher({ me }: { me?: Me | null }) {
  const t = useTranslations("language");
  const current = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [pending, startTransition] = useTransition();

  async function choose(locale: AppLocale) {
    if (locale === current) return;
    if (me) {
      const result = await api.PATCH("/api/v1/me", {
        body: { locale, expected_version: me.version },
      });
      if (result.data) queryClient.setQueryData(meQueryKey, result.data);
      else await queryClient.invalidateQueries({ queryKey: meQueryKey });
    }
    startTransition(() => router.replace(pathname, { locale }));
  }

  return (
    <nav aria-label={t("label")}>
      <ul className="flex gap-3">
        {locales.map((locale) => (
          <li key={locale}>
            <button
              type="button"
              lang={locale}
              dir={locale === "ar" ? "rtl" : "ltr"}
              aria-current={locale === current ? "true" : undefined}
              disabled={pending}
              onClick={() => void choose(locale)}
              className={locale === current ? "font-semibold underline" : "underline-offset-2 hover:underline"}
            >
              {t(locale)}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
