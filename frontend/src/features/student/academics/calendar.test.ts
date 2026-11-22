import { expect, test } from 'vitest';
import type { Lesson } from '../../../shared/academics/api';
import { weeklyCalendar } from './calendar';

test('calendar uses UTC, escapes content and excludes cancelled lessons', () => {
  const lesson: Lesson = {
    id: 'demo-event', subject: 'Проектирование, практикум; группа А',
    teacher: 'Иванов\nСТРОКА\\2', room: 'Аудитория '.repeat(20), status: 'moved',
    starts_at: '2026-11-23T08:00:00+03:00', ends_at: '2026-11-23T09:40:00+03:00', last_change: null,
  };
  const output = weeklyCalendar([lesson, {...lesson, id: 'cancelled', status: 'cancelled'}],
    new Date('2026-11-22T18:00:00Z'));
  for (const row of output.split('\r\n')) {
    expect(new TextEncoder().encode(row).length).toBeLessThanOrEqual(75);
  }
  const unfolded = output.replaceAll('\r\n ', '');
  expect(unfolded).toContain('DTSTART:20261123T050000Z\r\n');
  expect(unfolded).toContain('DTEND:20261123T064000Z\r\n');
  expect(unfolded).toContain('DESCRIPTION:Иванов\\nСТРОКА\\\\2\r\n');
  expect(unfolded).toContain('SUMMARY:Проектирование\\, практикум\\; группа А\r\n');
  expect(unfolded).not.toContain('cancelled');
  expect(output.endsWith('END:VCALENDAR\r\n')).toBe(true);
});
