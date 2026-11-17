import { useId, useState, type FormEvent } from 'react';
import { api } from '../../shared/api/client';
import { useSession } from '../../shared/api/session';
import { dateLabel, errorMessage, kindNames, localInput, statusNames, useApiPage,
  type Activity, type ActivityKind, type Assignment, type Learner, type Result, type ResultStatus } from '../../shared/academics/api';
import { Pagination } from '../../shared/academics/Pagination';
import styles from '../../shared/academics/Study.module.css';
import { Card } from '../../shared/ui/Card';
import { Page } from '../../shared/ui/Page';

export default function TeachingPage() {
  const session = useSession();
  return <Page title="Кабинет преподавателя" description="Задания, зачёты и результаты ваших групп.">
    {session.kind === 'loading' ? <p role="status">Проверяем доступ…</p>
      : session.kind === 'signed-in' && session.user.roles.includes('teacher') ? <TeacherWorkspace />
      : <Card title="Нужна роль преподавателя"><p>Назначения групп и дисциплин выдаёт администратор проекта.</p><a href="/auth/login/">Войти в другую учётную запись</a></Card>}
  </Page>;
}

function TeacherWorkspace() {
  const courses = useApiPage<Assignment>('/teaching/assignments/');
  const activities = useApiPage<Activity>('/teaching/activities/');
  const [editing, setEditing] = useState<Activity | null>(null);
  const [selected, setSelected] = useState<Activity | null>(null);
  const [formKey, setFormKey] = useState(0);
  function saved(activity: Activity) {
    activities.reload(); setEditing(null); setSelected(activity); setFormKey(value => value + 1);
  }
  return <div className={styles.stack}>
    <p className={styles.meta}>Дата и время отображаются в часовом поясе вашего устройства. Выставление результатов доступно только для назначенных вам групп и дисциплин.</p>
    <Card title="Мои дисциплины">
      {courses.loading && <p role="status">Загрузка назначений…</p>}
      {courses.error && <p role="alert">{courses.error}</p>}
      {courses.data && <>
        {!courses.data.count && <p>Назначений пока нет. Обратитесь к администратору.</p>}
        <ul>{courses.data.results.map(course => <li key={course.id}>{course.subject} — {course.group_name}, {course.term}</li>)}</ul>
        <Pagination data={courses.data} page={courses.page} setPage={courses.setPage} />
      </>}
    </Card>
    {courses.data && courses.data.count > 0 && <Card title={editing ? 'Изменить работу' : 'Новое задание или зачёт'}>
      <ActivityForm key={`${editing?.id ?? 'new'}-${editing?.revision ?? formKey}`}
        assignments={courses.data.results} initial={editing} onSaved={saved}
        cancel={() => setEditing(null)} />
    </Card>}
    <Card title="Мои задания и зачёты">
      {activities.loading && <p role="status">Загрузка работ…</p>}
      {activities.error && <div role="alert">{activities.error}<button onClick={activities.reload}>Повторить</button></div>}
      <div className={styles.stack}>{activities.data?.results.map(activity => <article className={styles.item} key={activity.id}>
        <span className={styles.badge}>{kindNames[activity.kind]}{activity.is_cancelled ? ' — отменено' : ''}</span>
        <h3>{activity.title}</h3>
        <p>{activity.subject} — {activity.group_name}</p>
        <p className={styles.meta}>{activity.term}. Начало: {dateLabel(activity.scheduled_at)}. Срок: {dateLabel(activity.due_at)}. {activity.room}</p>
        <p className={styles.description}>{activity.description}</p>
        <div className={styles.actions}>
          <button onClick={() => setSelected(activity)}>Ведомость: {activity.title}</button>
          <button className="button-secondary" onClick={() => setEditing(activity)}>Изменить: {activity.title}</button>
        </div>
      </article>)}</div>
      {activities.data && <>
        {!activities.data.count && <p>Создайте первую работу с помощью формы выше.</p>}
        <Pagination data={activities.data} page={activities.page} setPage={activities.setPage} />
      </>}
    </Card>
    {selected && <Roster key={selected.id} activity={selected} />}
  </div>;
}

function ActivityForm({ assignments, initial, onSaved, cancel }: {
  assignments: Assignment[]; initial: Activity | null; onSaved: (activity: Activity) => void; cancel: () => void;
}) {
  const fieldId = useId();
  const [kind, setKind] = useState<ActivityKind>(initial?.kind ?? 'homework');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const instant = (name: string) => form.get(name) ? new Date(String(form.get(name))).toISOString() : null;
      const body = { title: form.get('title'), description: form.get('description'), room: form.get('room'),
        scheduled_at: instant('scheduled_at'), due_at: instant('due_at'), is_cancelled: form.has('is_cancelled'),
        ...(initial ? {expected_revision: initial.revision} : {assignment: Number(form.get('assignment')), kind}) };
      const saved = await api<Activity>(initial ? `/teaching/activities/${initial.id}/` : '/teaching/activities/',
        {method: initial ? 'PATCH' : 'POST', body: JSON.stringify(body)});
      onSaved(saved);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  return <form className={styles.form} onSubmit={submit}>
    {error && <p role="alert" className="notice notice-error">{error}</p>}
    <div className={styles.fields}>
      <div className={styles.field}><label htmlFor={`${fieldId}-assignment`}>Дисциплина и группа</label>
        <select id={`${fieldId}-assignment`} name="assignment" required disabled={!!initial} defaultValue={initial?.assignment ?? ''}>
          <option value="" disabled>Выберите назначение</option>
          {initial && !assignments.some(item => item.id === initial.assignment) && <option value={initial.assignment}>{initial.subject} — {initial.group_name}</option>}
          {assignments.map(course => <option key={course.id} value={course.id}>{course.subject} — {course.group_name}</option>)}
        </select>
      </div>
      <div className={styles.field}><label htmlFor={`${fieldId}-kind`}>Вид работы</label>
        <select id={`${fieldId}-kind`} name="kind" value={kind} disabled={!!initial} onChange={event => setKind(event.target.value as ActivityKind)}>
          {Object.entries(kindNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
    </div>
    <label className={styles.field}>Название<input name="title" required maxLength={200} defaultValue={initial?.title ?? ''} /></label>
    <div className={styles.field}><label htmlFor={`${fieldId}-description`}>Задание или описание</label><textarea id={`${fieldId}-description`} name="description" maxLength={5000} defaultValue={initial?.description ?? ''} /></div>
    <div className={styles.fields}>
      <label className={styles.field}>Дата и время начала<input type="datetime-local" name="scheduled_at" required={kind !== 'homework'} defaultValue={localInput(initial?.scheduled_at ?? null)} /></label>
      <label className={styles.field}>Срок сдачи<input type="datetime-local" name="due_at" required={kind === 'homework'} defaultValue={localInput(initial?.due_at ?? null)} /></label>
      <label className={styles.field}>Аудитория<input name="room" maxLength={100} defaultValue={initial?.room ?? ''} /></label>
    </div>
    {initial && <label className={styles.check}><input type="checkbox" name="is_cancelled" defaultChecked={initial.is_cancelled} />Работа отменена</label>}
    <div className={styles.actions}>
      <button disabled={busy} type="submit">{busy ? 'Сохраняем…' : initial ? 'Сохранить изменения' : 'Создать работу'}</button>
      {initial && <button type="button" className="button-secondary" onClick={cancel}>Отменить редактирование</button>}
    </div>
  </form>;
}

function Roster({ activity }: {activity: Activity}) {
  const roster = useApiPage<Learner>(`/teaching/activities/${activity.id}/students/`);
  return <Card title={`Ведомость: ${activity.title}`}>
    <p className={styles.meta}>{activity.subject} — {activity.group_name}. Каждый результат сохраняется отдельно. Оценка 2, «Не зачтено» и «Задолженность» считаются долгом; успешная пересдача закрывает его.</p>
    {activity.is_cancelled && <p role="alert">Работа отменена. Выставление результатов отключено.</p>}
    <button type="button" className="button-secondary" onClick={roster.reload}>Обновить ведомость</button>
    {roster.loading && <p role="status">Загрузка студентов…</p>}
    {roster.error && <p role="alert">{roster.error}</p>}
    <div className={styles.stack}>{roster.data?.results.map(student => <GradeRow key={student.id}
      student={student} activity={activity} />)}</div>
    {roster.data && <>
      {!roster.data.count && <p>В этой группе пока нет студентов.</p>}
      <Pagination data={roster.data} page={roster.page} setPage={roster.setPage} />
    </>}
  </Card>;
}

function GradeRow({ student, activity }: {student: Learner; activity: Activity}) {
  const fieldId = useId();
  const [result, setResult] = useState(student.result);
  const [status, setStatus] = useState<ResultStatus | ''>(student.result?.status ?? '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setMessage(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const saved = await api<Result>(`/teaching/activities/${activity.id}/results/`, {method:'POST',
        body:JSON.stringify({student: student.id, expected_revision:result?.revision ?? 0, status,
          score:status === 'graded' ? Number(form.get('score')) : null, comment:form.get('comment')})});
      setResult(saved); setMessage('Результат сохранён');
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  return <form className={styles.item} onSubmit={submit} aria-label={`Результат: ${student.full_name}`}>
    <h3>{student.full_name}</h3>
    {result?.is_debt && <span className={`${styles.badge} ${styles.debt}`}>Задолженность</span>}
    <div className={styles.fields}>
      {/* Explicit labels keep the field name independent of option text and saved comments. */}
      <div className={styles.field}><label htmlFor={`${fieldId}-status`}>Результат</label><select id={`${fieldId}-status`} required value={status} onChange={event => setStatus(event.target.value as ResultStatus)}>
        <option value="" disabled>Выберите результат</option>
        {Object.entries(statusNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></div>
      <div className={styles.field}><label htmlFor={`${fieldId}-score`}>Оценка</label><select id={`${fieldId}-score`} name="score" required={status === 'graded'} disabled={status !== 'graded'} defaultValue={result?.score ?? ''}>
        <option value="" disabled>Выберите оценку</option>
        {[2,3,4,5].map(score => <option key={score} value={score}>{score}</option>)}
      </select></div>
    </div>
    <div className={styles.field}><label htmlFor={`${fieldId}-comment`}>Комментарий</label><textarea id={`${fieldId}-comment`} name="comment" maxLength={2000} defaultValue={result?.comment ?? ''} /></div>
    {error && <p role="alert" className="notice notice-error">{error}</p>}
    {message && <p role="status" className={styles.success}>{message}</p>}
    <div><button disabled={busy || activity.is_cancelled} type="submit">{busy ? 'Сохраняем…' : 'Сохранить результат'}</button></div>
  </form>;
}
