import { useEffect, useState } from 'react';
import { api, ApiError } from './client';

export interface StudentProfile { full_name: string; group: string; faculty: string; programme: string; course: number }
export interface Me {
  id: number; username: string; student_profile: null | StudentProfile; roles: string[];
  teacher_profile: null | {full_name: string; faculty: string; is_active: boolean};
}

export type Session = { kind: 'loading' } | { kind: 'signed-in'; user: Me } | { kind: 'anonymous' } | { kind: 'error' };

/** Who is signed in, for chrome such as the header. The server still enforces access;
 *  this only decides whether to show a name or a "Войти" link. Sign-in and sign-out
 *  are full page navigations, so reading once per page load is enough. */
export function useSession(): Session {
  const [session, setSession] = useState<Session>({ kind: 'loading' });
  useEffect(() => {
    const controller = new AbortController();
    api<Me>('/me/', { signal: controller.signal }).then(
      (user) => { if (!controller.signal.aborted) setSession({ kind: 'signed-in', user }); },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setSession({ kind: error instanceof ApiError && error.status === 403 ? 'anonymous' : 'error' });
      },
    );
    return () => controller.abort();
  }, []);
  return session;
}

export function displayName(user: Me): string {
  return user.student_profile?.full_name ?? user.teacher_profile?.full_name ?? user.username;
}

/** Two letters for an avatar: first letters of the surname and first name. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

/** "Иванов Иван Иванович" → "Иван". Anything that is not a full three-part name
 *  (a login, a two-word display name) is used whole rather than guessed at. */
export function firstName(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts.length === 3 ? parts[1] : name.trim();
}
