export function addHours(d: Date, hours: number): Date {
  const r = new Date(d)
  r.setHours(r.getHours() + hours)
  return r
}

export function addMinutes(d: Date, minutes: number): Date {
  const r = new Date(d)
  r.setMinutes(r.getMinutes() + minutes)
  return r
}

export function roundToHour(d: Date): Date {
  const r = new Date(d)
  if (r.getMinutes() > 0 || r.getSeconds() > 0 || r.getMilliseconds() > 0) {
    r.setHours(r.getHours() + 1, 0, 0, 0)
  } else {
    r.setMinutes(0, 0, 0)
  }
  return r
}
