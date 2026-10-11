"use client";

// Neutral temporary layout (Stage 1). No visual design decisions here: they
// come from the direction chosen in Stage 1b (docs/design-brief.md).
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, type ReactNode } from "react";

import { Bidi } from "@/components/Bidi";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { api, fetchMe, meQueryKey, type Me } from "@/lib/api";

export function useMe() {
  return useQuery({ queryKey: meQueryKey, queryFn: fetchMe });
}

export function AppShell({ children }: { children: (me: Me) => ReactNode }) {
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const me = useMe();

  useEffect(() => {
    if (me.data === null) router.replace("/login");
  }, [me.data, router]);

  if (me.isPending || me.data === null) {
    return <p className="p-6">{t("shell.loading")}</p>;
  }
  if (me.isError) {
    return (
      <div role="alert" className="p-6 space-y-3">
        <p>{t("shell.apiUnavailable")}</p>
        <button type="button" className="underline" onClick={() => void me.refetch()}>
          {t("shell.retry")}
        </button>
      </div>
    );
  }

  const user = me.data;

  async function logout() {
    await api.POST("/api/v1/auth/logout");
    queryClient.setQueryData(meQueryKey, null);
    router.replace("/login");
  }

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:p-2">
        {t("shell.skipToContent")}
      </a>
      <header className="flex flex-wrap items-center justify-between gap-4 border-b p-4">
        <div>
          <p className="font-semibold">{t("app.short")}</p>
          <p className="text-sm">{t("app.name")}</p>
        </div>
        <LanguageSwitcher me={user} />
        <div className="text-sm text-end">
          <p>
            {t("shell.signedInAs")} <span data-testid="user-email"><Bidi>{user.email}</Bidi></span>
          </p>
          <p>
            {user.roles.map((role) => t(`roles.${role}`)).join(", ")}
          </p>
          <button type="button" className="underline" onClick={() => void logout()}>
            {t("auth.logout")}
          </button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav aria-label={t("shell.mainNav")} className="w-56 shrink-0 border-e p-4">
          <ul className="space-y-2" data-testid="main-nav">
            {user.nav.map((item) => (
              <li key={item.key} data-nav-key={item.key}>
                <Link
                  href={item.path}
                  aria-current={pathname === item.path ? "page" : undefined}
                  className={pathname === item.path ? "font-semibold" : "hover:underline"}
                >
                  {t(`nav.${item.key}` as Parameters<typeof t>[0])}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <main id="main" className="flex-1 p-6">
          {children(user)}
        </main>
      </div>
      <footer className="border-t p-4 text-sm">{t("app.temporaryLayout")}</footer>
    </div>
  );
}
