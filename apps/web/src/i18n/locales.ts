// Interface locales. French is the default; Arabic is right-to-left.
// Italian is planned (spec §12) and stays disabled until translations are reviewed.
export const locales = ["fr", "ar", "en"] as const;
export type AppLocale = (typeof locales)[number];
export const defaultLocale: AppLocale = "fr";

const rtlLocales: ReadonlySet<string> = new Set(["ar"]);

export function isAppLocale(value: string): value is AppLocale {
  return (locales as readonly string[]).includes(value);
}

export function directionOf(locale: string): "rtl" | "ltr" {
  return rtlLocales.has(locale) ? "rtl" : "ltr";
}

// BCP 47 tags for Intl formatting. Tunisia writes Western digits in Arabic text.
export const intlLocale: Record<AppLocale, string> = {
  fr: "fr-TN",
  ar: "ar-TN-u-nu-latn",
  en: "en-GB",
};
