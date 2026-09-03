import { z } from 'zod'

export interface BookingFormValues {
  mode: 'train' | 'dev' | 'cpu'
  projectId: number | null
  serverId: number | null
  gpuIds: number[]
  start: Date | null
  end: Date | null
  schedule: 'continuous' | 'daily'
  dailyStart: string
  dailyEnd: string
  description: string
}

export interface BookingInterval {
  start: Date
  end: Date
}

const FULL_HOUR_TIME = /^(?:[01]\d|2[0-3]):00$/

function hourFromTime(value: string): number {
  return Number(value.slice(0, 2))
}

export function buildDailyIntervals(
  rangeStart: Date,
  rangeEnd: Date,
  dailyStart: string,
  dailyEnd: string,
): BookingInterval[] {
  if (
    rangeEnd <= rangeStart ||
    !FULL_HOUR_TIME.test(dailyStart) ||
    !FULL_HOUR_TIME.test(dailyEnd) ||
    dailyStart >= dailyEnd
  ) {
    return []
  }

  const intervals: BookingInterval[] = []
  const day = new Date(rangeStart)
  day.setHours(0, 0, 0, 0)
  while (day < rangeEnd) {
    const scheduledStart = new Date(day)
    scheduledStart.setHours(hourFromTime(dailyStart), 0, 0, 0)
    const scheduledEnd = new Date(day)
    scheduledEnd.setHours(hourFromTime(dailyEnd), 0, 0, 0)
    const start = new Date(Math.max(scheduledStart.getTime(), rangeStart.getTime()))
    const end = new Date(Math.min(scheduledEnd.getTime(), rangeEnd.getTime()))
    if (end.getTime() - start.getTime() >= 3600_000) intervals.push({ start, end })
    day.setDate(day.getDate() + 1)
  }
  return intervals
}

export function createBookingSchema(isAdmin: boolean, maxBookingDays: number) {
  return z
    .object({
      mode: z.enum(['train', 'dev', 'cpu']),
      projectId: z.number().nullable(),
      serverId: z.number().nullable(),
      gpuIds: z.array(z.number()),
      start: z.date().nullable(),
      end: z.date().nullable(),
      schedule: z.enum(['continuous', 'daily']),
      dailyStart: z.string(),
      dailyEnd: z.string(),
      description: z.string(),
    })
    .superRefine((v, ctx) => {
      if (v.projectId == null) {
        ctx.addIssue({ code: 'custom', message: 'Bitte ein Projekt wählen.', path: ['projectId'] })
      }
      if (!v.start) {
        ctx.addIssue({ code: 'custom', message: 'Bitte Startzeit wählen.', path: ['start'] })
        return
      }
      if (!v.end) {
        ctx.addIssue({ code: 'custom', message: 'Bitte Endzeit wählen.', path: ['end'] })
        return
      }
      const hasSubHourPart = (d: Date) =>
        d.getMinutes() !== 0 || d.getSeconds() !== 0 || d.getMilliseconds() !== 0
      if (hasSubHourPart(v.start)) {
        ctx.addIssue({
          code: 'custom',
          message: 'Start muss auf einer vollen Stunde liegen.',
          path: ['start'],
        })
      }
      if (hasSubHourPart(v.end)) {
        ctx.addIssue({
          code: 'custom',
          message: 'Ende muss auf einer vollen Stunde liegen.',
          path: ['end'],
        })
      }
      if (v.end <= v.start) {
        ctx.addIssue({ code: 'custom', message: 'Ende muss nach dem Start liegen.', path: ['end'] })
      }
      const hours = (v.end.getTime() - v.start.getTime()) / 3600_000
      if (hours < 1) {
        ctx.addIssue({ code: 'custom', message: 'Mindestdauer ist 1 Stunde.', path: ['end'] })
      }
      if (!isAdmin && hours > maxBookingDays * 24) {
        ctx.addIssue({
          code: 'custom',
          message: `Maximale Dauer ist ${maxBookingDays} ${maxBookingDays === 1 ? 'Tag' : 'Tage'} (${maxBookingDays * 24} h).`,
          path: ['end'],
        })
      }
      if (v.schedule === 'daily') {
        if (!FULL_HOUR_TIME.test(v.dailyStart)) {
          ctx.addIssue({
            code: 'custom',
            message: 'Der tägliche Start muss auf einer vollen Stunde liegen.',
            path: ['dailyStart'],
          })
        }
        if (!FULL_HOUR_TIME.test(v.dailyEnd)) {
          ctx.addIssue({
            code: 'custom',
            message: 'Das tägliche Ende muss auf einer vollen Stunde liegen.',
            path: ['dailyEnd'],
          })
        }
        if (v.dailyStart >= v.dailyEnd) {
          ctx.addIssue({
            code: 'custom',
            message: 'Das tägliche Ende muss nach dem täglichen Start liegen.',
            path: ['dailyEnd'],
          })
        } else if (
          FULL_HOUR_TIME.test(v.dailyStart) &&
          FULL_HOUR_TIME.test(v.dailyEnd) &&
          buildDailyIntervals(v.start, v.end, v.dailyStart, v.dailyEnd).length === 0
        ) {
          ctx.addIssue({
            code: 'custom',
            message: 'Die tägliche Zeitspanne liegt außerhalb des gewählten Zeitraums.',
            path: ['dailyEnd'],
          })
        }
      }
      if (v.mode !== 'cpu' && v.gpuIds.length === 0) {
        ctx.addIssue({
          code: 'custom',
          message: 'Bitte mindestens eine GPU wählen.',
          path: ['gpuIds'],
        })
      }
      if (v.mode === 'cpu' && v.serverId == null) {
        ctx.addIssue({
          code: 'custom',
          message: 'Bitte einen Server wählen.',
          path: ['serverId'],
        })
      }
    })
}
