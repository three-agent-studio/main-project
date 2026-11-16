import { useState } from 'react';
import { useSession } from '../../../shared/api/session';
import { dateLabel, kindNames, statusNames, useApiPage,
  type Activity, type Lesson, type Result } from '../../../shared/academics/api';
import { Pagination } from '../../../shared/academics/Pagination';
import styles from '../../../shared/academics/Study.module.css';
import { Card } from '../../../shared/ui/Card';
import { Page } from '../../../shared/ui/Page';

export default function AcademicsPage() {
  const session = useSession();
  return <Page title="Учёба" description="Расписание, задания и ваши результаты.">
    {session.kind === 'loading' ? <p role="status">Загрузка…</p>
      : session.kind === 'signed-in' && session.user.roles.includes('student') ? <StudentWorkspace />
      : <Card title="Нужен профиль студента"><a href="/auth/login/">Войти в кабинет</a></Card>}
  </Page>;
}

function StudentWorkspace() {
  const [debtsOnly, setDebtsOnly] = useState(false);
  const lessons = useApiPage<Lesson>('/lessons/');
  const activities = useApiPage<Activity>('/activities/');
  return <div className={styles.stack}>
    <p className={styles.meta}>Дата и время отображаются в часовом поясе вашего устройства.</p>
    <Card title="Расписание на текущую неделю">
      {lessons.loading && <p role="status">Загрузка расписания…</p>}
      {lessons.error && <div role="alert">{lessons.error}<button onClick={lessons.reload}>Повторить</button></div>}
      <div className={styles.stack}>{lessons.data?.results.map(lesson => <article className={styles.item} key={lesson.id}>
        <h3>{lesson.subject}</h3><p>{dateLabel(lesson.starts_at)} — {dateLabel(lesson.ends_at)}</p>
        <p className={styles.meta}>{lesson.teacher}. Аудитория: {lesson.room}</p>
        {lesson.status !== 'scheduled' && <span className={styles.badge}>{lesson.status === 'cancelled' ? 'Отменено' : 'Перенесено'}</span>}
        {lesson.last_change && <p>{lesson.last_change.reason}</p>}
      </article>)}</div>
      {lessons.data && <>{!lessons.data.count && <p>На этой неделе занятий пока нет.</p>}
        <Pagination data={lessons.data} page={lessons.page} setPage={lessons.setPage} /></>}
    </Card>
    <Card title="Задания и сессия">
      {activities.loading && <p role="status">Загрузка заданий…</p>}
      {activities.error && <div role="alert">{activities.error}<button onClick={activities.reload}>Повторить</button></div>}
      <div className={styles.stack}>{activities.data?.results.map(activity => <article className={styles.item} key={activity.id}>
        <span className={styles.badge}>{kindNames[activity.kind]}{activity.is_cancelled ? ' — отменено' : ''}</span>
        <h3>{activity.title}</h3><p>{activity.subject} — {activity.term}</p>
        <p className={styles.description}>{activity.description}</p>
        <p className={styles.meta}>Начало: {dateLabel(activity.scheduled_at)}. Срок сдачи: {dateLabel(activity.due_at)}. {activity.room}</p>
        <p className={styles.meta}>Преподаватель: {activity.teacher}</p>
      </article>)}</div>
      {activities.data && <>{!activities.data.count && <p>Заданий и дат зачётов пока нет.</p>}
        <Pagination data={activities.data} page={activities.page} setPage={activities.setPage} /></>}
    </Card>
    <Card title="Успеваемость">
      <label className={styles.check}><input type="checkbox" checked={debtsOnly}
        onChange={event => setDebtsOnly(event.target.checked)} />Только задолженности</label>
      <Results key={String(debtsOnly)} debtsOnly={debtsOnly} />
    </Card>
  </div>;
}

function Results({ debtsOnly }: {debtsOnly: boolean}) {
  const results = useApiPage<Result>(`/assessments/${debtsOnly ? '?debt=true' : ''}`);
  return <>
    {results.loading && <p role="status">Загрузка результатов…</p>}
    {results.error && <div role="alert">{results.error}<button onClick={results.reload}>Повторить</button></div>}
    <div className={styles.stack}>{results.data?.results.map(result => <article className={styles.item} key={result.id}>
      <h3>{result.activity.subject}: {result.activity.title}</h3>
      <span className={`${styles.badge} ${result.is_debt ? styles.debt : ''}`}>
        {statusNames[result.status]}{result.score !== null ? `: ${result.score}` : ''}
      </span>
      {result.is_debt && result.status !== 'debt' && <p>Есть задолженность — уточните условия пересдачи у преподавателя.</p>}
      <p className={styles.meta}>{result.activity.term}</p>
      <p className={styles.description}>{result.comment}</p>
    </article>)}</div>
    {results.data && <>{!results.data.count && <p>{debtsOnly ? 'Задолженностей нет.' : 'Оценки пока не выставлены.'}</p>}
      <Pagination data={results.data} page={results.page} setPage={results.setPage} /></>}
  </>;
}
