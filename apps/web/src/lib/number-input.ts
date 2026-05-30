export function parseRequiredNumberInput(value: string): number {
  return value === "" ? Number.NaN : Number(value);
}

export function requiredNumberInputValue(value: number): number | "" {
  return Number.isFinite(value) ? value : "";
}
