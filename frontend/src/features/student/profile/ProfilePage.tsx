import { useEffect, useState } from 'react';
import { api, ApiError } from '../../../shared/api/client';
import { Card } from '../../../shared/ui/Card';
import { Page } from '../../../shared/ui/Page';

interface Me {
  id: number;
  username: string;
  student_profile: null | { full_name: string; group: string; faculty: string; programme: string; course: number };
}
type State = { kind: 'loading' } | { kind: 'ready'; user: Me } | { kind: 'anonymous' } | { kind: 'error' };

export default function ProfilePage() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const [logoutError, setLogoutError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: 'loading' });
    api<Me>('/me/', { signal: controller.signal }).then(
      (user) => { if (!controller.signal.aborted) setState({ kind: 'ready', user }); },
      (error: unknown) => {
        if (!controller.signal.aborted) setState({ kind: error instanceof ApiError && error.status === 403 ? 'anonymous' : 'error' });
      },
    );
    return () => controller.abort(); // Route changes must not apply stale responses to a new screen.
  }, [attempt]);

  async function logout() {
    setLogoutError(false);
    try {
      const { csrfToken } = await api<{ csrfToken: string }>('/csrf/');
      const response = await fetch('/auth/logout/', {
        method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken },
      });
      if (!response.ok) throw new Error('Logout failed');
      // Full navigation drops all in-memory private state after the server invalidates the session.
      window.location.replace('/');
    } catch { setLogoutError(true); }
  }

  return <Page title="Мой профиль">
    {state.kind === 'loading' && <p role="status">Загрузка профиля…</p>}
    {state.kind === 'anonymous' && <Card title="Необходимо войти"><a className="button" href="/auth/login/?next=/profile">Войти в кабинет</a></Card>}
    {state.kind === 'error' && <><p role="alert">Не удалось загрузить профиль.</p><button onClick={() => setAttempt(attempt + 1)}>Повторить</button></>}
    {state.kind === 'ready' && <>
      <Card title={state.user.student_profile?.full_name ?? state.user.username}>
        {state.user.student_profile ? <dl>
          {Object.entries({ Факультет: state.user.student_profile.faculty, Направление: state.user.student_profile.programme, Курс: state.user.student_profile.course, Группа: state.user.student_profile.group }).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
        </dl> : <p>Для этой учётной записи профиль студента ещё не создан.</p>}
      </Card>
      {logoutError && <p role="alert">Не удалось выйти. Повторите попытку.</p>}
      <button onClick={logout}>Выйти</button>
    </>}
  </Page>;
}
