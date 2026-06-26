/** Schedule draft model shared by the editor and the form. No components. */

import type { ScheduleKind } from "./api";

export type IntervalUnit = "minutes" | "hours" | "days";

export interface ScheduleDraft {
  schedule_kind: ScheduleKind;
  intervalAmount: number;
  intervalUnit: IntervalUnit;
  cronHour: number;
  cronMinute: number;
  maxRuns: string; // empty string = unlimited
}

const UNIT_MINUTES: Record<IntervalUnit, number> = {
  minutes: 1,
  hours: 60,
  days: 1440,
};

/** Fold a draft's interval amount + unit into total minutes. */
export function draftIntervalMinutes(draft: ScheduleDraft): number {
  return Math.max(1, draft.intervalAmount) * UNIT_MINUTES[draft.intervalUnit];
}
