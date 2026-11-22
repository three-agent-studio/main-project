import type { Lesson } from '../../../shared/academics/api';

function escapeText(value: string) {
  return value.replaceAll('\\', '\\\\').replace(/\r\n|\r|\n/g, '\\n').replace(/[;,]/g, '\\$&');
}

function utc(value: string | Date) {
  return new Date(value).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

function fold(line: string) {
  // Calendar lines are folded by UTF-8 byte count, never inside a Cyrillic character.
  const encoder = new TextEncoder();
  let output = '';
  let width = 0;
  for (const char of line) {
    const bytes = encoder.encode(char).length;
    if (width + bytes > 75) {
      output += '\r\n ';
      width = 1;
    }
    output += char;
    width += bytes;
  }
  return output;
}

export function weeklyCalendar(lessons: Lesson[], stamp = new Date()) {
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Digital Deanery//Weekly Schedule//RU', 'CALSCALE:GREGORIAN'];
  for (const lesson of lessons) {
    if (lesson.status === 'cancelled') continue;
    lines.push(
      'BEGIN:VEVENT',
      `UID:${escapeText(lesson.id)}@digital-deanery`,
      `DTSTAMP:${utc(stamp)}`,
      `DTSTART:${utc(lesson.starts_at)}`,
      `DTEND:${utc(lesson.ends_at)}`,
      `SUMMARY:${escapeText(lesson.subject)}`,
      `LOCATION:${escapeText(lesson.room)}`,
      `DESCRIPTION:${escapeText(lesson.teacher)}`,
      'END:VEVENT',
    );
  }
  return [...lines, 'END:VCALENDAR', ''].map(fold).join('\r\n');
}

export function downloadCalendar(lessons: Lesson[], monday: string) {
  const url = URL.createObjectURL(new Blob([weeklyCalendar(lessons)], { type: 'text/calendar;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `deanery-${monday}.ics`;
  document.body.append(link);
  link.click();
  link.remove();
  // Mobile browsers may start the download after the click handler returns.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
