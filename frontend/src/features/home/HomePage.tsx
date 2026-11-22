import type { ComponentType } from 'react';
import { Link } from 'react-router';
import { displayName, firstName, useSession } from '../../shared/api/session';
import { BellIcon, CalendarIcon, GradesIcon, RequestIcon } from '../../shared/ui/icons';
import { moscowDateKey } from '../student/academics/schedule';
import { TodayCard } from './TodayCard';
import styles from './HomePage.module.css';

const dayLabel = new Intl.DateTimeFormat('ru-RU', {
  timeZone: 'Europe/Moscow', weekday: 'long', day: 'numeric', month: 'long',
});
const moscowHour = new Intl.DateTimeFormat('en', {
  timeZone: 'Europe/Moscow', hour: 'numeric', hourCycle: 'h23',
});

function greeting(hour: number): string {
  if (hour < 5) return 'Доброй ночи';
  if (hour < 12) return 'Доброе утро';
  if (hour < 18) return 'Добрый день';
  return 'Добрый вечер';
}

const upcoming: { title: string; text: string; Icon: ComponentType; to: string }[] = [
  { title: 'Расписание', text: 'Пары на текущую неделю, аудитории и переносы.', Icon: CalendarIcon, to: '/academics' },
  { title: 'Успеваемость', text: 'Задания, оценки, зачёты и задолженности.', Icon: GradesIcon, to: '/academics' },
  { title: 'Заявки и справки', text: 'Заказ справки онлайн и статус без очереди в деканат.', Icon: RequestIcon, to: '/requests' },
  { title: 'Уведомления', text: 'Объявления деканата и напоминания о сроках.', Icon: BellIcon, to: '/notifications' },
];

export default function HomePage() {
  const session = useSession();
  const now = new Date();
  const hello = greeting(Number(moscowHour.format(now)));
  const user = session.kind === 'signed-in' ? session.user : null;

  const student = user?.roles.includes('student');

  return <div className={styles.home}>
    <section className={styles.welcome} aria-labelledby="home-title">
      <time className={styles.date} dateTime={moscowDateKey(now)}>{dayLabel.format(now)} · МСК</time>
      <h1 id="home-title">{user ? `${hello}, ${firstName(displayName(user))}` : 'Учёба под рукой'}</h1>
      <p className={styles.lead}>Здесь собрано всё, что связано с учёбой: от расписания до справок из деканата.</p>
      <div className={styles.actions}>
        {user?.roles.includes('student') && <>
          <Link className="button" to="/academics">Открыть расписание и оценки</Link>
          <Link className="button button-secondary" to="/profile">Мой профиль</Link>
        </>}
        {user?.roles.includes('deanery_staff') && <Link className="button" to="/deanery">Открыть кабинет деканата</Link>}
        {user && !user.roles.includes('student') && !user.roles.includes('deanery_staff') && (user.roles.includes('teacher')
          ? <Link className="button" to="/teaching">Открыть кабинет преподавателя</Link>
          : <Link className="button" to="/profile">Открыть мой профиль</Link>)}
        {!user && session.kind !== 'loading' && <a className="button" href="/auth/login/">Войти в кабинет</a>}
      </div>
    </section>

    {user?.roles.includes('student') && <TodayCard key={user.id} />}
    <section aria-labelledby="upcoming-title">
      <h2 id="upcoming-title" className={styles.sectionTitle}>{student ? 'Быстрый переход' : 'Возможности кабинета'}</h2>
      <ul className={styles.upcoming}>
        {upcoming.map(({ title, text, Icon, to }) => <li key={title} className={student ? styles.shortcut : undefined}>
          <span className={styles.icon}><Icon /></span>
          <div><h3>{student ? <Link to={to}>{title}<span className={styles.arrow} aria-hidden="true">↗</span></Link> : title}</h3><p>{text}</p></div>
        </li>)}
      </ul>
    </section>
  </div>;
}
