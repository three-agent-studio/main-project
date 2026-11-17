import { describe, expect, it, vi } from 'vitest';
import { api } from '../../../shared/api/client';
import type { Lesson } from '../../../shared/academics/api';
import { groupWeek, loadWeek, moscowDateKey, moscowMonday, moscowTime } from './schedule';

vi.mock('../../../shared/api/client', () => ({api: vi.fn()}));
const lesson = (id: string, start: string, end: string): Lesson => ({
  id, subject: 'Высшая математика', teacher: 'Лебедев Артём Сергеевич', room: 'ДЕМО-А · 201',
  starts_at: start, ends_at: end, status: 'scheduled', last_change: null,
});

describe('Moscow calendar', () => {
  it('uses Moscow Monday even while UTC is still Sunday', () => {
    const now = new Date('2026-11-15T21:30:00Z');
    expect(moscowDateKey(now)).toBe('2026-11-16');
    expect(moscowMonday(now)).toBe('2026-11-16');
    expect(moscowMonday(new Date('2026-11-22T12:00:00Z'))).toBe('2026-11-16');
    expect(moscowTime('2026-11-16T05:00:00Z')).toBe('08:00');
  });
  it('includes all seven days and sorts classes without changing its input', () => {
    const lessons = [lesson('later', '2026-11-16T07:00:00Z', '2026-11-16T08:40:00Z'),
      lesson('first', '2026-11-16T05:00:00Z', '2026-11-16T06:40:00Z')];
    const days = groupWeek(lessons, '2026-11-16');
    expect(days.map(day => day.title)).toEqual(['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']);
    expect(days[0].lessons.map(item => item.id)).toEqual(['first', 'later']);
    expect(days[6].lessons).toEqual([]);
    expect(lessons[0].id).toBe('later');
  });
  it('assigns UTC late-night starts to the right Moscow date and respects midnight end', () => {
    const days = groupWeek([
      lesson('monday', '2026-11-15T22:00:00Z', '2026-11-15T23:00:00Z'),
      lesson('carry', '2026-11-15T20:30:00Z', '2026-11-15T21:30:00Z'),
      lesson('exclusive', '2026-11-15T20:00:00Z', '2026-11-15T21:00:00Z'),
    ], '2026-11-16');
    expect(days[0].lessons.map(item => item.id)).toEqual(['carry', 'monday']);
    expect(days[1].lessons).toEqual([]);
  });
});

describe('complete weekly schedule', () => {
  it('combines every API page of a day using relative URLs only', async () => {
    const first = lesson('one', '2026-11-16T05:00:00Z', '2026-11-16T06:40:00Z');
    const second = lesson('two', '2026-11-16T07:00:00Z', '2026-11-16T08:40:00Z');
    vi.mocked(api).mockReset().mockResolvedValueOnce({count: 2, results: [first], next: 'https://foreign.invalid/api/v1/lessons/?page=2'})
      .mockResolvedValueOnce({count: 2, results: [second], next: null});
    const signal = new AbortController().signal;
    const loaded = await loadWeek('2026-11-16', signal);
    expect(groupWeek(loaded, '2026-11-16')[0].lessons).toHaveLength(2);
    expect(vi.mocked(api).mock.calls.map(call => call[0])).toEqual([
      '/lessons/?from=2026-11-16&to=2026-11-22&page=1',
      '/lessons/?from=2026-11-16&to=2026-11-22&page=2',
    ]);
  });
  it('fails the whole load when a later page fails', async () => {
    vi.mocked(api).mockReset().mockResolvedValueOnce({count:2, results:[lesson('one', '2026-11-16T05:00:00Z', '2026-11-16T06:40:00Z')], next:'?page=2'})
      .mockRejectedValueOnce(new Error('Network unavailable'));
    await expect(loadWeek('2026-11-16', new AbortController().signal)).rejects.toThrow('Network unavailable');
  });
});
