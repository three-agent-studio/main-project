import type { ComponentType } from 'react';
import { Link } from 'react-router';
import { displayName, firstName, useSession } from '../../shared/api/session';
import { BellIcon, CalendarIcon, GradesIcon, RequestIcon } from '../../shared/ui/icons';
import styles from './HomePage.module.css';

function greeting(hour: number): string {
  if (hour < 5) return 'Доброй ночи';
  if (hour < 12) return 'Доброе утро';
  if (hour < 18) return 'Добрый день';
  return 'Добрый вечер';
}

// Honest roadmap: these sections have no API yet (Issues #7–#9), so the home
// screen describes them instead of showing invented timetable or grade data.
const upcoming: { title: string; text: string; Icon: ComponentType }[] = [
  { title: 'Расписание', text: 'Пары на сегодня и неделю, аудитории и переносы.', Icon: CalendarIcon },
  { title: 'Успеваемость', text: 'Оценки, зачёты и сессия в одном списке.', Icon: GradesIcon },
  { title: 'Заявки и справки', text: 'Заказ справки онлайн и статус без очереди в деканат.', Icon: RequestIcon },
  { title: 'Уведомления', text: 'Объявления деканата и напоминания о сроках.', Icon: BellIcon },
];

export default function HomePage() {
  const session = useSession();
  const hello = greeting(new Date().getHours());
  const user = session.kind === 'signed-in' ? session.user : null;

  return <div className={styles.home}>
    <section className={styles.welcome} aria-labelledby="home-title">
      <h1 id="home-title">{user ? `${hello}, ${firstName(displayName(user))}` : `${hello}!`}</h1>
      <p className={styles.lead}>Здесь собрано всё, что связано с учёбой: от расписания до справок из деканата.</p>
      {user
        ? <Link className="button" to="/profile">Открыть мой профиль</Link>
        : session.kind !== 'loading' && <a className="button" href="/auth/login/">Войти в кабинет</a>}
    </section>

    <section aria-labelledby="upcoming-title">
      <h2 id="upcoming-title" className={styles.sectionTitle}>Скоро в кабинете</h2>
      <ul className={styles.upcoming}>
        {upcoming.map(({ title, text, Icon }) => <li key={title}>
          <span className={styles.icon}><Icon /></span>
          <div><h3>{title}</h3><p>{text}</p></div>
          <span className={styles.status}>В разработке</span>
        </li>)}
      </ul>
    </section>
  </div>;
}
