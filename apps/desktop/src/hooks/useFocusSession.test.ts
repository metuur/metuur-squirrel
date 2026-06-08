import { describe, expect, it } from "vitest";
import { deriveElapsedMinutes } from "./useFocusSession";
import type { OpenSession } from "../api/client";

function sessionAt(checkin_at: string): OpenSession {
  return { project_slug: "p", intent_slug: "i", checkin_at };
}

describe("deriveElapsedMinutes", () => {
  it("returns 0 when there is no open session", () => {
    expect(deriveElapsedMinutes(null, Date.now())).toBe(0);
  });

  it("derives elapsed minutes from a UTC checkin against an absolute now", () => {
    // checkin_at is UTC (backend writes ...+00:00); now is an absolute epoch.
    const checkinMs = Date.parse("2026-06-07T12:00:00+00:00");
    expect(deriveElapsedMinutes(sessionAt("2026-06-07T12:00:00+00:00"), checkinMs)).toBe(0);
    expect(deriveElapsedMinutes(sessionAt("2026-06-07T12:00:00+00:00"), checkinMs + 7 * 60000)).toBe(7);
    // 90 seconds → floors to 1 minute.
    expect(deriveElapsedMinutes(sessionAt("2026-06-07T12:00:00+00:00"), checkinMs + 90_000)).toBe(1);
  });

  it("is timezone-correct: a `Z` and a `+00:00` checkin yield the same elapsed", () => {
    const now = Date.parse("2026-06-07T13:00:00Z"); // 1h after checkin
    expect(deriveElapsedMinutes(sessionAt("2026-06-07T12:00:00Z"), now)).toBe(60);
    expect(deriveElapsedMinutes(sessionAt("2026-06-07T12:00:00+00:00"), now)).toBe(60);
  });

  it("clamps negative elapsed (clock skew) to 0", () => {
    const checkinMs = Date.parse("2026-06-07T12:00:00Z");
    expect(deriveElapsedMinutes(sessionAt("2026-06-07T12:00:00Z"), checkinMs - 5 * 60000)).toBe(0);
  });

  it("returns 0 for an unparseable checkin timestamp", () => {
    expect(deriveElapsedMinutes(sessionAt("not-a-date"), Date.now())).toBe(0);
  });
});
