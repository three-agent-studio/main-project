import { useState } from 'react';
import { useSession } from '../../../shared/api/session';
import { dateLabel, kindNames, statusNames, useApiPage,
  type Activity, type Result } from '../../../shared/academics/api';
import { Pagination } from '../../../shared/academics/Pagination';
import styles from '../../../shared/academics/Study.module.css';
import { Badge, type BadgeTone } from '../../../shared/ui/Badge';
import { Card } from '../../../shared/ui/Card';
import { EmptyState } from '../../../shared/ui/EmptyState';
import { Page } from '../../../shared/ui/Page';
import { ScheduleWeek } from './ScheduleWeek';

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
  const activities = useApiPage<Activity>('/activities/');
  return <div className={styles.stack}>
    <ScheduleWeek />
    <Card title="Задания и сессия">
      <p className={styles.meta}>Время заданий и зачётов — в часовом поясе вашего устройства.</p>
      {activities.loading && <p role="status">Загрузка заданий…</p>}
      {activities.error && <div role="alert" className="notice notice-error">{activities.error} <button onClick={activities.reload}>Повторить</button></div>}
      <div className={styles.list}>{activities.data?.results.map(activity => <article className={styles.item} key={activity.id}>
        <div className={styles.itemHead}>
          <Badge>{kindNames[activity.kind]}</Badge>
          {activity.is_cancelled && <Badge tone="danger">Отменено</Badge>}
        </div>
        <h3>{activity.title}</h3>
        <p className={styles.subject}>{activity.subject}, {activity.term}</p>
        {activity.description && <p className={styles.description}>{activity.description}</p>}
        <dl className={styles.facts}>
          {activity.scheduled_at && <div><dt>Начало</dt><dd>{dateLabel(activity.scheduled_at)}</dd></div>}
          {activity.due_at && <div><dt>Срок сдачи</dt><dd>{dateLabel(activity.due_at)}</dd></div>}
          {activity.room && <div><dt>Аудитория</dt><dd>{activity.room}</dd></div>}
          <div><dt>Преподаватель</dt><dd>{activity.teacher}</dd></div>
        </dl>
      </article>)}</div>
      {activities.data && <>{!activities.data.count && <EmptyState title="Заданий и дат зачётов пока нет">Новые работы появятся здесь, как только преподаватель их добавит.</EmptyState>}
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
    {results.error && <div role="alert" className="notice notice-error">{results.error} <button onClick={results.reload}>Повторить</button></div>}
    <div className={styles.list}>{results.data?.results.map(result => <article className={styles.item} key={result.id}>
      <div className={styles.itemTitle}>
        <div>
          <h3>{result.activity.subject}: {result.activity.title}</h3>
          <p className={styles.subject}>{result.activity.term}</p>
        </div>
        {result.score !== null && <p className={`${styles.score} ${result.is_debt ? styles.scoreDebt : ''}`} aria-hidden="true">{result.score}</p>}
      </div>
      <div className={styles.itemHead}>
        <Badge tone={resultTone(result)}>{statusNames[result.status]}{result.score !== null ? `: ${result.score}` : ''}</Badge>
      </div>
      {result.is_debt && result.status !== 'debt' && <p className={styles.meta}>Есть задолженность — уточните условия пересдачи у преподавателя.</p>}
      {result.comment && <p className={styles.description}>{result.comment}</p>}
    </article>)}</div>
    {results.data && <>{!results.data.count && <EmptyState title={debtsOnly ? 'Задолженностей нет' : 'Оценки пока не выставлены'}>
      {debtsOnly ? 'Все работы сданы или ещё не оценены.' : 'Результаты появятся после проверки работ преподавателем.'}</EmptyState>}
      <Pagination data={results.data} page={results.page} setPage={results.setPage} /></>}
  </>;
}

/** Debts are the only red; a pass or a good grade is green; the rest stay neutral. */
function resultTone(result: Result): BadgeTone {
  if (result.is_debt || result.status === 'failed' || result.status === 'debt') return 'danger';
  if (result.status === 'passed' || (result.score !== null && result.score >= 4)) return 'success';
  return 'info';
}
