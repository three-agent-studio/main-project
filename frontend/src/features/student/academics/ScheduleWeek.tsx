import { useEffect, useId, useState } from 'react';
import { errorMessage } from '../../../shared/academics/api';
import type { Lesson } from '../../../shared/academics/api';
import { Card } from '../../../shared/ui/Card';
import { groupWeek, loadWeek, moscowDateKey, moscowDateTitle, moscowMonday, moscowTime } from './schedule';
import styles from './ScheduleWeek.module.css';

export function ScheduleWeek() {
  const id = useId();
  const [today] = useState(() => moscowDateKey(new Date()));
  const [monday] = useState(() => moscowMonday(new Date()));
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{attempt: number; lessons?: Lesson[]; error?: string}>();
  useEffect(() => {
    const controller = new AbortController();
    loadWeek(monday, controller.signal).then(
      lessons => { if (!controller.signal.aborted) setState({attempt, lessons}); },
      error => { if (!controller.signal.aborted) setState({attempt, error: errorMessage(error)}); },
    );
    return () => controller.abort();
  }, [monday, attempt]);
  const current = state?.attempt === attempt ? state : undefined;
  const days = groupWeek(current?.lessons ?? [], monday);
  return <Card title="Расписание на текущую неделю">
    <div className={styles.intro}>
      <p>{days[0].date} — {days[6].date}</p>
      <span className={styles.zone}>Московское время · МСК</span>
    </div>
    {!current && <p role="status">Загрузка расписания…</p>}
    {current?.error && <div role="alert" className="notice notice-error">
      <p>{current.error}</p><button onClick={() => setAttempt(value => value + 1)}>Повторить</button>
    </div>}
    {current?.lessons && <div className={styles.days}>
      {days.map(day => <section className={styles.day} key={day.key} aria-labelledby={`${id}-${day.key}`}>
        <header className={`${styles.dayHeader} ${day.key === today ? styles.today : ''}`}>
          <div><h3 id={`${id}-${day.key}`}>{day.title}</h3><p>{day.date}</p></div>
          {day.key === today ? <span className={styles.todayLabel}>Сегодня</span>
            : <span className={styles.count}>Занятий: {day.lessons.length}</span>}
        </header>
        {day.lessons.length ? <ol className={styles.lessons}>
          {day.lessons.map(lesson => <li className={styles.lesson} key={lesson.id}>
            <div className={styles.clock}>
              <time dateTime={lesson.starts_at}>{moscowTime(lesson.starts_at)}</time>
              <span>МСК</span><span className={styles.end}>до {moscowTime(lesson.ends_at)}</span>
            </div>
            <div className={styles.details}>
              <h4>{lesson.subject}</h4>
              <p className={styles.room}><span>Аудитория</span> {lesson.room}</p>
              <p className={styles.teacher}><span>Преподаватель</span> {lesson.teacher}</p>
              {moscowDateKey(lesson.starts_at) !== day.key && <p className={styles.note}>
                Продолжение занятия с {moscowDateTitle(lesson.starts_at)}
              </p>}
              {lesson.status !== 'scheduled' && <span className={`${styles.status} ${lesson.status === 'cancelled' ? styles.cancelled : ''}`}>
                {lesson.status === 'cancelled' ? 'Отменено' : 'Перенесено'}
              </span>}
              {lesson.status !== 'scheduled' && lesson.last_change && <p className={styles.note}>{lesson.last_change.reason}</p>}
            </div>
          </li>)}
        </ol> : <p className={styles.empty}>Занятий нет — свободный день</p>}
      </section>)}
    </div>}
  </Card>;
}
