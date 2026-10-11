import { intlLocale, isAppLocale } from "@/i18n/locales";

export const DISPLAY_TIME_ZONE = "Africa/Tunis";

// Timestamps are stored in UTC and displayed in Africa/Tunis (CLAUDE.md).
export function formatDateTime(isoUtc: string, locale: string): string {
  const tag = isAppLocale(locale) ? intlLocale[locale] : intlLocale.fr;
  return new Intl.DateTimeFormat(tag, {
    dateStyle: "medium",
    timeStyle: "short",
    hourCycle: "h23",
    timeZone: DISPLAY_TIME_ZONE,
  }).format(new Date(isoUtc));
}
