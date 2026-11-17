import { useEffect, useState } from 'react';
import { api, ApiError } from '../api/client';

export interface Assignment { id: number; group: number; group_name: string; subject: string; term: string }
export type ActivityKind = 'homework' | 'test' | 'credit' | 'exam';
export interface Activity {
  id: string; assignment: number; subject: string; term: string; group_name: string; teacher: string;
  kind: ActivityKind; title: string; description: string; scheduled_at: string | null;
  due_at: string | null; room: string; is_cancelled: boolean; revision: number;
}
export type ResultStatus = 'graded' | 'passed' | 'failed' | 'debt';
export interface Result {
  id: string; student: number; activity: Activity; status: ResultStatus; score: number | null;
  comment: string; revision: number; is_debt: boolean;
}
export interface Learner { id: number; full_name: string; result: Result | null }
export interface Lesson {
  id: string; subject: string; teacher: string; room: string; starts_at: string; ends_at: string;
  status: 'scheduled' | 'moved' | 'cancelled'; last_change: null | { reason: string };
}
export interface ApiPage<T> { count: number; next: string | null; previous: string | null; results: T[] }

/** A response belongs to its exact URL/reload key; stale data never flashes for another class. */
export function useApiPage<T>(path: string) {
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const url = `${path}${path.includes('?') ? '&' : '?'}page=${page}`;
  const key = `${url}|${attempt}`;
  const [state, setState] = useState<{ key: string; data?: ApiPage<T>; error?: string }>({ key: '' });
  useEffect(() => {
    const controller = new AbortController();
    api<ApiPage<T>>(url, { signal: controller.signal }).then(
      data => { if (!controller.signal.aborted) setState({ key, data }); },
      error => { if (!controller.signal.aborted) setState({ key, error: errorMessage(error) }); },
    );
    return () => controller.abort();
  }, [url, key]);
  const current = state.key === key ? state : undefined;
  return { data: current?.data, error: current?.error, loading: !current,
    page, setPage, reload: () => setAttempt(value => value + 1) };
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const collect = (value: unknown): string[] => typeof value === 'string' ? [value]
      : Array.isArray(value) ? value.flatMap(collect)
      : value && typeof value === 'object' ? Object.values(value).flatMap(collect) : [];
    const messages = collect(error.details);
    if (messages.length) return messages.join(' ');
  }
  return 'Не удалось выполнить действие. Проверьте соединение и повторите попытку.';
}

export const kindNames: Record<ActivityKind, string> = {
  homework: 'Домашнее задание', test: 'Контрольная', credit: 'Зачёт', exam: 'Экзамен',
};
export const statusNames: Record<ResultStatus, string> = {
  graded: 'Оценка', passed: 'Зачтено', failed: 'Не зачтено', debt: 'Задолженность',
};
export function dateLabel(value: string | null) {
  return value ? new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZoneName: 'short' }).format(new Date(value)) : 'Не назначено';
}
export function localInput(value: string | null) {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
