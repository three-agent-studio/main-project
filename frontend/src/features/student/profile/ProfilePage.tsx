import { useEffect, useState } from 'react';
import { api, ApiError } from '../../../shared/api/client';
import { displayName, initials, type Me } from '../../../shared/api/session';
import { Card } from '../../../shared/ui/Card';
import { Page } from '../../../shared/ui/Page';
import styles from './ProfilePage.module.css';

type State = { kind: 'loading' } | { kind: 'ready'; user: Me } | { kind: 'anonymous' } | { kind: 'error' };

export default function ProfilePage() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const [logoutError, setLogoutError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
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
      // Django owns the destination after logout. A full navigation also drops
      // private React state instead of reopening the old public home screen.
      window.location.replace(response.url);
    } catch { setLogoutError(true); }
  }

  return <Page title="Мой профиль">
    {state.kind === 'loading' && <p role="status" className="notice">Загружаем профиль…</p>}
    {state.kind === 'anonymous' && <Card title="Войдите, чтобы увидеть профиль">
      <p>Профиль доступен только владельцу учётной записи.</p>
      <a className="button" href="/auth/login/?next=/profile">Войти в кабинет</a>
    </Card>}
    {state.kind === 'error' && <div className={styles.error}>
      <p role="alert" className="notice notice-error">Не удалось загрузить профиль. Проверьте интернет и попробуйте ещё раз.</p>
      <button onClick={() => { setState({ kind: 'loading' }); setAttempt(attempt + 1); }}>Повторить</button>
    </div>}
    {state.kind === 'ready' && <>
      <ProfileCard user={state.user} />
      {logoutError && <p role="alert" className="notice notice-error">Не удалось выйти. Повторите попытку.</p>}
      <button className="button-secondary" onClick={logout}>Выйти</button>
    </>}
  </Page>;
}

/** The student card: the one bold element of the cabinet, modelled on a student ID. */
function ProfileCard({ user }: { user: Me }) {
  const name = displayName(user);
  const profile = user.student_profile;
  return <article className={styles.card} aria-labelledby="profile-name">
    <div className={styles.cardTop}>
      <span className={styles.avatar} aria-hidden="true">{initials(name)}</span>
      <div className={styles.identity}>
        <h2 id="profile-name">{name}</h2>
        {profile && <p className={styles.group}>группа <span>{profile.group}</span></p>}
      </div>
    </div>
    {profile
      ? <dl className={styles.details}>
        {Object.entries({ Факультет: profile.faculty, Направление: profile.programme, Курс: profile.course })
          .map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>
      : <p className={styles.empty}>Для этой учётной записи ещё нет профиля студента. Его создаёт сотрудник деканата.</p>}
  </article>;
}
