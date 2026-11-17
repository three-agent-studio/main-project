import { api } from '../../../shared/api/client';
import type { ApiPage, Lesson } from '../../../shared/academics/api';

export const MOSCOW_ZONE = 'Europe/Moscow';
const dateParts = new Intl.DateTimeFormat('en', {
  timeZone: MOSCOW_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
});
const clock = new Intl.DateTimeFormat('ru-RU', {
  timeZone: MOSCOW_ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});
const weekday = new Intl.DateTimeFormat('ru-RU', {timeZone: MOSCOW_ZONE, weekday: 'long'});
const dateTitle = new Intl.DateTimeFormat('ru-RU', {timeZone: MOSCOW_ZONE, day: 'numeric', month: 'long'});

export function moscowDateKey(value: Date | string): string {
  const parts = dateParts.formatToParts(new Date(value));
  const part = (type: string) => parts.find(item => item.type === type)!.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}
export function moscowTime(value: string): string { return clock.format(new Date(value)); }
export function moscowDateTitle(value: string): string { return dateTitle.format(new Date(value)); }

// Calendar arithmetic uses UTC noon; the device's timezone must not move a day.
function shiftDay(key: string, days: number): string {
  const date = new Date(`${key}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
export function moscowMonday(now: Date): string {
  const key = moscowDateKey(now);
  const day = new Date(`${key}T12:00:00Z`).getUTCDay();
  return shiftDay(key, -((day + 6) % 7));
}

export function groupWeek(lessons: Lesson[], monday: string) {
  const ordered = [...lessons].sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at) || a.id.localeCompare(b.id));
  return Array.from({length: 7}, (_, offset) => {
    const key = shiftDay(monday, offset);
    const noon = new Date(`${key}T12:00:00Z`);
    const name = weekday.format(noon);
    return { key, title: name[0].toUpperCase() + name.slice(1), date: dateTitle.format(noon),
      // Include a class continuing after midnight; an exact midnight end is exclusive.
      lessons: ordered.filter(lesson => moscowDateKey(lesson.starts_at) <= key
        && moscowDateKey(new Date(Date.parse(lesson.ends_at) - 1)) >= key),
    };
  });
}

export async function loadWeek(monday: string, signal: AbortSignal): Promise<Lesson[]> {
  const lessons = new Map<string, Lesson>();
  const period = `from=${monday}&to=${shiftDay(monday, 6)}`;
  for (let number = 1; ; number++) {
    // Follow page numbers on our relative endpoint, never a server-provided origin.
    // A day must not split into unrelated blocks at the API's 25-row boundary.
    const page = await api<ApiPage<Lesson>>(`/lessons/?${period}&page=${number}`, {signal});
    page.results.forEach(lesson => lessons.set(lesson.id, lesson));
    if (!page.next) return [...lessons.values()];
    if (!page.results.length) throw new Error('Empty intermediate schedule page');
  }
}
