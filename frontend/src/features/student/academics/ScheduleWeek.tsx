import { useEffect, useId, useState } from 'react';
import { errorMessage } from '../../../shared/academics/api';
import type { Lesson } from '../../../shared/academics/api';
import { Badge } from '../../../shared/ui/Badge';
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
      <p className={styles.range}>{days[0].date} — {days[6].date}</p>
      <span className={styles.zone}>Московское время · МСК</span>
    </div>
    {!current && <p role="status">Загрузка расписания…</p>}
    {current?.error && <div role="alert" className="notice notice-error">
      <p>{current.error}</p><button onClick={() => setAttempt(value => value + 1)}>Повторить</button>
    </div>}
    {current?.lessons && <div className={styles.days}>
      {days.map(day => <section className={`${styles.day} ${day.key === today ? styles.today : ''}`} key={day.key} aria-labelledby={`${id}-${day.key}`}>
        <header className={styles.dayHeader}>
          <h3 id={`${id}-${day.key}`}>{day.title}</h3>
          <p>{day.date}</p>
          {day.key === today ? <Badge tone="info">Сегодня</Badge>
            : day.lessons.length > 0 && <span className={styles.count}>Занятий: {day.lessons.length}</span>}
        </header>
        {day.lessons.length ? <ol className={styles.lessons}>
          {day.lessons.map(lesson => <li className={`${styles.lesson} ${lesson.status === 'cancelled' ? styles.cancelledRow : ''}`} key={lesson.id}>
            <p className={styles.clock}>
              <time dateTime={lesson.starts_at}>{moscowTime(lesson.starts_at)}</time>
              <span className={styles.end}>до {moscowTime(lesson.ends_at)}</span>
            </p>
            <div className={styles.details}>
              <h4>{lesson.subject}</h4>
              <p className={styles.teacher}><span className="sr-only">Преподаватель: </span>{lesson.teacher}</p>
              {moscowDateKey(lesson.starts_at) !== day.key && <p className={styles.note}>
                Продолжение занятия с {moscowDateTitle(lesson.starts_at)}
              </p>}
              {lesson.status !== 'scheduled' && <div className={styles.change}>
                <Badge tone={lesson.status === 'cancelled' ? 'danger' : 'warning'}>
                  {lesson.status === 'cancelled' ? 'Отменено' : 'Перенесено'}
                </Badge>
                {lesson.last_change && <p className={styles.note}>{lesson.last_change.reason}</p>}
              </div>}
            </div>
            <p className={styles.room}><span className={styles.roomLabel}>Аудитория</span><span>{lesson.room}</span></p>
          </li>)}
        </ol> : <p className={styles.empty}>Занятий нет — свободный день</p>}
      </section>)}
    </div>}
  </Card>;
}
