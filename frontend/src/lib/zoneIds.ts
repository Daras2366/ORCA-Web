const ZONE_ID_PATTERN = /\b(PFZ\d{4}|GRID_\d{4})\b/gi;

export function extractZoneIds(text: string): string[] {
  const seen = new Set<string>();
  const ids: string[] = [];

  for (const match of text.matchAll(ZONE_ID_PATTERN)) {
    const raw = match[1];
    if (!raw) continue;
    const id = raw.toUpperCase();
    if (!seen.has(id)) {
      seen.add(id);
      ids.push(id);
    }
  }

  return ids;
}

export function getZoneLineContext(text: string, zoneId: string): string | null {
  const escaped = zoneId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const linePattern = new RegExp(escaped, "i");

  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (trimmed && linePattern.test(trimmed)) {
      return trimmed;
    }
  }

  return null;
}
