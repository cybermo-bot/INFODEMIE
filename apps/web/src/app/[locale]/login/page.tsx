import { hasLocale, useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use } from "react";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { LoginForm } from "@/components/LoginForm";
import { routing } from "@/i18n/routing";

export default function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = use(params);
  if (hasLocale(routing.locales, locale)) setRequestLocale(locale);
  const t = useTranslations();

  return (
    <main className="mx-auto max-w-xl space-y-6 p-6">
      <LanguageSwitcher />
      <div>
        <p className="font-semibold">{t("app.short")}</p>
        <p>{t("app.name")}</p>
      </div>
      <h1 className="text-xl font-semibold">{t("auth.title")}</h1>
      <LoginForm />
      <p className="text-sm">{t("app.temporaryLayout")}</p>
    </main>
  );
}
