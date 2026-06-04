export function percent(value: unknown, digits = 1): string {
  const num = asNumber(value);
  return num === null ? "--" : `${(num * 100).toFixed(digits)}%`;
}

export function number(value: unknown, digits = 3): string {
  const num = asNumber(value);
  return num === null ? "--" : num.toFixed(digits);
}

export function integer(value: unknown): string {
  const num = asNumber(value);
  return num === null ? "--" : Math.round(num).toString();
}

export function text(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return String(value);
}

export function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

export function entries(record: Record<string, unknown> | undefined): Array<[string, unknown]> {
  if (!record) return [];
  return Object.entries(record);
}
