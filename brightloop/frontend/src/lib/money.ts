// Money is stored as integer paise (BIGINT). We only format it here, in the UI.
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });
const inrWhole = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatMoney(paise: number, opts: { whole?: boolean } = {}): string {
  return (opts.whole ? inrWhole : inr).format(paise / 100);
}

// "2026-10-31" -> "31 Oct 2026". Parsed by hand so timezones can't shift the day.
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
