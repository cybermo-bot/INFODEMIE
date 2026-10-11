"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { useRouter } from "@/i18n/navigation";
import { api, meQueryKey } from "@/lib/api";

type LoginError = "invalid" | "throttled" | "unavailable";

export function LoginForm() {
  const t = useTranslations("auth");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<LoginError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.POST("/api/v1/auth/login", {
        body: { email: String(form.get("email")), password: String(form.get("password")) },
      });
      if (result.data) {
        queryClient.setQueryData(meQueryKey, result.data);
        // The language saved on the account wins after login.
        router.replace("/", { locale: result.data.locale });
        return;
      }
      const status = result.response.status;
      setError(status === 429 ? "throttled" : status === 401 || status === 422 ? "invalid" : "unavailable");
    } catch {
      setError("unavailable");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4 max-w-sm" noValidate>
      <label className="flex flex-col gap-1">
        <span>{t("email")}</span>
        <input
          name="email"
          type="email"
          dir="ltr"
          autoComplete="username"
          required
          className="border p-2"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span>{t("password")}</span>
        <input
          name="password"
          type="password"
          dir="ltr"
          autoComplete="current-password"
          required
          className="border p-2"
        />
      </label>
      {error && (
        <p role="alert" data-testid="login-error">
          {t(error)}
        </p>
      )}
      <button type="submit" disabled={submitting} className="border p-2">
        {submitting ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}
