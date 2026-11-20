import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { api, ApiError } from '../../../shared/api/client';
import { displayName, initials, type Me } from '../../../shared/api/session';
import { Badge } from '../../../shared/ui/Badge';
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
      {state.user.teacher_profile && !state.user.student_profile
        ? <TeacherCard user={state.user} /> : <ProfileCard user={state.user} />}
      <div className={styles.columns}>
        <Shortcuts user={state.user} />
        <section className={styles.section} aria-labelledby="account-title">
          <h2 id="account-title">Учётная запись</h2>
          <dl className={styles.facts}>
            <div><dt>Логин</dt><dd>{state.user.username}</dd></div>
            <div><dt>Сеанс</dt><dd>Активен в этом браузере</dd></div>
          </dl>
          {logoutError && <p role="alert" className="notice notice-error">Не удалось выйти. Повторите попытку.</p>}
          <button className="button-secondary" onClick={logout}>Выйти</button>
        </section>
      </div>
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
      <h2 id="profile-name" className={styles.name}>{name}</h2>
      {profile && <p className={styles.group}><span className={styles.groupLabel}>Группа</span><span>{profile.group}</span></p>}
    </div>
    {profile
      ? <dl className={styles.details}>
        {Object.entries({ Факультет: profile.faculty, Направление: profile.programme, Курс: profile.course })
          .map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>
      : <p className={styles.empty}>Для этой учётной записи ещё нет профиля студента. Его создаёт сотрудник деканата.</p>}
  </article>;
}

/** Same cover as the student card, so every role gets one recognisable identity block. */
function TeacherCard({ user }: { user: Me }) {
  const name = displayName(user);
  const teacher = user.teacher_profile!;
  return <article className={styles.card} aria-labelledby="profile-name">
    <div className={styles.cardTop}>
      <span className={styles.avatar} aria-hidden="true">{initials(name)}</span>
      <h2 id="profile-name" className={styles.name}>{name}</h2>
      <p className={styles.group}><span className={styles.groupLabel}>Роль</span><span className={styles.role}>Преподаватель</span></p>
    </div>
    <dl className={styles.details}>
      <div><dt>Факультет</dt><dd>{teacher.faculty}</dd></div>
      <div><dt>Доступ к ведомостям</dt><dd>{teacher.is_active ? 'Открыт' : 'Приостановлен'}</dd></div>
    </dl>
  </article>;
}

type Shortcut = { title: string; text: string; to?: string };

/** Where people usually go next from their profile. Unbuilt sections are shown honestly. */
function Shortcuts({ user }: { user: Me }) {
  const items: Shortcut[] = user.roles.includes('student') ? [
    { title: 'Расписание на неделю', text: 'Пары, аудитории и переносы.', to: '/academics' },
    { title: 'Оценки и задолженности', text: 'Результаты работ и что пересдать.', to: '/academics' },
    { title: 'Заявки и справки', text: 'Справка об обучении без очереди.' },
  ] : user.roles.includes('teacher') ? [
    { title: 'Кабинет преподавателя', text: 'Задания, зачёты и ведомости групп.', to: '/teaching' },
  ] : [];
  if (!items.length) return null;
  return <section className={styles.section} aria-labelledby="shortcuts-title">
    <h2 id="shortcuts-title">Быстрые переходы</h2>
    <ul className={styles.shortcuts}>
      {items.map(item => <li key={item.title}>
        {item.to ? <Link to={item.to}>{item.title}</Link> : <span className={styles.shortcutTitle}>{item.title}</span>}
        <span className={styles.shortcutText}>{item.text}</span>
        {!item.to && <Badge>В разработке</Badge>}
      </li>)}
    </ul>
  </section>;
}
