// Money is stored as integer paise (BIGINT). Formatting happens only in the UI.
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });
const inrWhole = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

/**
 * Format paise as INR. Supports both the shared UI's { whole } option and
 * the earlier (currency, locale) signature for callers that still use it.
 */
export function formatMoney(
  paise: number,
  optionsOrCurrency: { whole?: boolean } | string = {},
  locale = "en-IN",
): string {
  if (typeof optionsOrCurrency === "string") {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: optionsOrCurrency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(paise / 100);
  }
  return (optionsOrCurrency.whole ? inrWhole : inr).format(paise / 100);
}

// Parse date-only values as UTC so local timezones cannot shift the calendar day.
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
