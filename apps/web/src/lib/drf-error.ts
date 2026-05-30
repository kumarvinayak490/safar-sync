export function extractDrfErrorMessage(
  payload: unknown,
  preferredFields: string[] = []
): string | null {
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const record = payload as Record<string, unknown>;

    for (const field of preferredFields) {
      const message = extractDrfErrorMessage(record[field]);
      if (message) {
        return message;
      }
    }
  }

  return firstMessage(payload);
}

function firstMessage(value: unknown): string | null {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return firstMessage(value[0]);
  }

  if (value && typeof value === "object") {
    for (const nestedValue of Object.values(value)) {
      const nestedMessage = firstMessage(nestedValue);
      if (nestedMessage) {
        return nestedMessage;
      }
    }
  }

  return null;
}
