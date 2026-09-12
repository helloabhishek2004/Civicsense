/**
 * CivicSense Dashboard — Production Date & Timestamp Utilities
 *
 * Ensures accurate UTC parsing and localization across all browsers and devices.
 * Prevents timezone shifting bugs where ISO date-time strings without explicit Z
 * or offset are erroneously interpreted by ECMAScript engines as browser local time.
 */

/**
 * Parses an ISO date-time string as UTC, even if the backend or source
 * omitted the trailing 'Z' or timezone offset.
 */
export function parseUtcDate(input: string | Date | null | undefined): Date | null {
  if (!input) return null;

  if (input instanceof Date) {
    return isNaN(input.getTime()) ? null : input;
  }

  if (typeof input !== 'string') return null;

  const trimmed = input.trim();
  if (!trimmed) return null;

  // Check if string already has a timezone indicator ('Z', 'z', or '+HH:MM' / '-HH:MM')
  const hasTimezone = /[zZ]$|[+-]\d{2}(:?\d{2})?$/.test(trimmed);

  let normalized = trimmed;
  if (!hasTimezone) {
    // If it looks like an ISO date-time (e.g. 2026-09-12T10:07:04.321 or 2026-09-12 10:07:04)
    if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(trimmed)) {
      normalized = trimmed.replace(' ', 'T') + 'Z';
    }
  }

  const date = new Date(normalized);
  if (!isNaN(date.getTime())) {
    return date;
  }

  // Fallback to native parsing
  const fallback = new Date(trimmed);
  return isNaN(fallback.getTime()) ? null : fallback;
}

/**
 * Normalizes an ISO date string to guaranteed UTC ending with 'Z'.
 */
export function normalizeIsoUtc(input: string | null | undefined): string {
  if (!input) return '';
  const parsed = parseUtcDate(input);
  return parsed ? parsed.toISOString() : input;
}

/**
 * Formats a timestamp into a compact short string, e.g. "Sep 12 • 03:37 PM".
 */
export function formatDateShort(
  input: string | Date | null | undefined,
  locale?: string
): string {
  const date = parseUtcDate(input);
  if (!date) return '—';

  const datePart = date.toLocaleDateString(locale, {
    month: 'short',
    day: 'numeric',
  });
  const timePart = date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
  });

  return `${datePart} • ${timePart}`;
}

/**
 * Formats a timestamp into standard date and time, e.g. "12 Sep 2026, 03:37 PM".
 */
export function formatDateTime(
  input: string | Date | null | undefined,
  locale?: string
): string {
  const date = parseUtcDate(input);
  if (!date) return '—';

  const datePart = date.toLocaleDateString(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
  const timePart = date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
  });

  return `${datePart}, ${timePart}`;
}

/**
 * Formats a full exact timestamp for tooltips, e.g. "Saturday, 12 Sep 2026, 03:37:04 PM GMT+5:30".
 */
export function formatDateFull(
  input: string | Date | null | undefined,
  locale?: string
): string {
  const date = parseUtcDate(input);
  if (!date) return '—';

  return date.toLocaleString(locale, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short',
  });
}

/**
 * Formats time only, e.g. "03:37 PM".
 */
export function formatTime(
  input: string | Date | null | undefined,
  locale?: string
): string {
  const date = parseUtcDate(input);
  if (!date) return '—';

  return date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Formats relative time elapsed from now, e.g. "Just now", "5m ago", "2h ago", "Yesterday", "3d ago".
 */
export function formatRelativeTime(
  input: string | Date | null | undefined,
  nowInput?: Date
): string {
  const date = parseUtcDate(input);
  if (!date) return '—';

  const now = nowInput ?? new Date();
  const diffMs = now.getTime() - date.getTime();

  // If slightly in future due to clock drift (within 30 seconds)
  if (diffMs < 30_000 && diffMs > -30_000) {
    return 'Just now';
  }

  if (diffMs < 0) {
    return 'Recently';
  }

  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSec < 60) {
    return 'Just now';
  }
  if (diffMin < 60) {
    return `${diffMin}m ago`;
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  if (diffDays === 1) {
    return 'Yesterday';
  }
  if (diffDays < 30) {
    return `${diffDays}d ago`;
  }

  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
