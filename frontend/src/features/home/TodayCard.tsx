import { Link } from 'react-router';
import { useApiPage, type Lesson } from '../../shared/academics/api';
import { Card } from '../../shared/ui/Card';
import { moscowDateKey, moscowTime } from '../student/academics/schedule';
import styles from './HomePage.module.css';

export function TodayCard() {
  const day = moscowDateKey(new Date());
  const today = useApiPage<Lesson>(`/lessons/?from=${day}&to=${day}`);
  const lessons = today.data?.results.filter(lesson => lesson.status !== 'cancelled');
  return <Card title="Сегодня по МСК">
    {today.loading && <p role="status">Загружаем пары…</p>}
    {today.error && <div className="notice notice-error" role="alert">
      {today.error} <button onClick={today.reload}>Повторить</button>
    </div>}
    {lessons?.length === 0 && <p>{today.data?.next ? 'Остальные занятия доступны в расписании.' : 'Активных занятий сегодня нет.'}</p>}
    {!!lessons?.length && <ol className={styles.todayLessons}>
      {lessons.slice(0, 3).map(lesson => <li key={lesson.id}>
        <time dateTime={lesson.starts_at}>{moscowTime(lesson.starts_at)}</time>
        <strong>{lesson.subject}</strong> <span>{lesson.room}</span>
      </li>)}
    </ol>}
    <Link to="/academics">Открыть всё расписание</Link>
  </Card>;
}
