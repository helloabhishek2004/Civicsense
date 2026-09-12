import { describe, it, expect } from 'vitest';
import {
  parseUtcDate,
  normalizeIsoUtc,
  formatDateShort,
  formatDateTime,
  formatDateFull,
  formatTime,
  formatRelativeTime,
} from '../core/utils/dateUtils';

describe('dateUtils', () => {
  describe('parseUtcDate', () => {
    it('returns null for empty or null inputs', () => {
      expect(parseUtcDate(null)).toBeNull();
      expect(parseUtcDate(undefined)).toBeNull();
      expect(parseUtcDate('')).toBeNull();
      expect(parseUtcDate('   ')).toBeNull();
    });

    it('returns the same Date if already a valid Date object', () => {
      const d = new Date(Date.UTC(2026, 8, 12, 10, 7, 4));
      expect(parseUtcDate(d)).toBe(d);
    });

    it('parses ISO date string with Z as exact UTC time', () => {
      const parsed = parseUtcDate('2026-09-12T10:07:04.321Z');
      expect(parsed).not.toBeNull();
      expect(parsed?.toISOString()).toBe('2026-09-12T10:07:04.321Z');
    });

    it('parses naive ISO date-time string (without Z) as UTC time to prevent local offset shift', () => {
      const naive = '2026-09-12T10:07:04.321792';
      const parsed = parseUtcDate(naive);
      expect(parsed).not.toBeNull();
      // Should match the UTC timestamp rather than being shifted by local timezone
      expect(parsed?.getUTCFullYear()).toBe(2026);
      expect(parsed?.getUTCMonth()).toBe(8); // September (0-indexed)
      expect(parsed?.getUTCDate()).toBe(12);
      expect(parsed?.getUTCHours()).toBe(10);
      expect(parsed?.getUTCMinutes()).toBe(7);
      expect(parsed?.getUTCSeconds()).toBe(4);
    });

    it('parses ISO string with explicit timezone offset correctly', () => {
      const withOffset = '2026-09-12T15:37:04.321+05:30';
      const parsed = parseUtcDate(withOffset);
      expect(parsed).not.toBeNull();
      expect(parsed?.getUTCHours()).toBe(10);
      expect(parsed?.getUTCMinutes()).toBe(7);
    });
  });

  describe('normalizeIsoUtc', () => {
    it('normalizes naive ISO string to explicit UTC string ending with Z', () => {
      const normalized = normalizeIsoUtc('2026-09-12T10:07:04.000');
      expect(normalized).toBe('2026-09-12T10:07:04.000Z');
    });

    it('preserves already normalized UTC strings', () => {
      const normalized = normalizeIsoUtc('2026-09-12T10:07:04.000Z');
      expect(normalized).toBe('2026-09-12T10:07:04.000Z');
    });
  });

  describe('formatDateShort & formatDateTime', () => {
    it('formats short date containing month, day, and time', () => {
      const formatted = formatDateShort('2026-09-12T10:07:00Z', 'en-US');
      expect(formatted).toContain('Sep 12');
      expect(formatted).toContain('•');
    });

    it('formats date time containing year, month, day, and time', () => {
      const formatted = formatDateTime('2026-09-12T10:07:00Z', 'en-US');
      expect(formatted).toContain('Sep 12, 2026');
    });

    it('returns fallback dash for invalid inputs', () => {
      expect(formatDateShort(null)).toBe('—');
      expect(formatDateTime(undefined)).toBe('—');
      expect(formatDateFull('')).toBe('—');
      expect(formatTime(null)).toBe('—');
    });
  });

  describe('formatRelativeTime', () => {
    const fixedNow = new Date('2026-09-12T10:07:00Z');

    it('returns "Just now" for recent times', () => {
      const past20s = new Date('2026-09-12T10:06:45Z');
      expect(formatRelativeTime(past20s, fixedNow)).toBe('Just now');
    });

    it('returns minutes ago', () => {
      const past5m = new Date('2026-09-12T10:02:00Z');
      expect(formatRelativeTime(past5m, fixedNow)).toBe('5m ago');
    });

    it('returns hours ago', () => {
      const past3h = new Date('2026-09-12T07:07:00Z');
      expect(formatRelativeTime(past3h, fixedNow)).toBe('3h ago');
    });

    it('returns Yesterday', () => {
      const past26h = new Date('2026-09-11T08:07:00Z');
      expect(formatRelativeTime(past26h, fixedNow)).toBe('Yesterday');
    });
  });
});
