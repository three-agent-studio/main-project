import { useId, useState, type FormEvent } from 'react';
import { errorMessage, useApiPage } from '../../shared/academics/api';
import { api, ApiError } from '../../shared/api/client';
import form from '../../shared/ui/Form.module.css';
import styles from './Deanery.module.css';
import { AnnouncementForm } from './AnnouncementForm';
import { RolePage } from './RolePage';
import { TicketList } from './TicketList';
import type { Ticket } from './tickets';

export default function StaffPage() {
  return <RolePage role="deanery_staff" title="Кабинет деканата" description="Принимайте заявки студентов своего факультета и оставляйте ответы.">
    <StaffQueue />
    <AnnouncementForm />
  </RolePage>;
}

function StaffQueue() {
  const query = useApiPage<Ticket>('/staff/requests/');
  const [notice, setNotice] = useState('');
  return <>
    <div><button className="button-secondary" onClick={query.reload}>Обновить очередь</button></div>
    {notice && <p role="status">{notice}</p>}
    <TicketList staff query={query} action={ticket => (
      ticket.status === 'submitted' || ticket.status === 'in_progress'
        ? <Transition ticket={ticket} onSaved={() => {
          setNotice('Статус заявки обновлён.');
          query.reload();
        }} onRefresh={query.reload} />
        : null
    )} />
  </>;
}

function Transition({ ticket, onSaved, onRefresh }: {
  ticket: Ticket; onSaved: () => void; onRefresh: () => void;
}) {
  const commentId = useId();
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [stale, setStale] = useState(false);
  const pending = ticket.status === 'submitted';

  async function transition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || stale) return;
    const sender = (event.nativeEvent as SubmitEvent).submitter;
    const status = sender instanceof HTMLButtonElement ? sender.value : '';
    if (!status) return;
    setSaving(true);
    setError('');
    try {
      await api<Ticket>(`/staff/requests/${ticket.id}/status/`, {
        method: 'POST',
        body: JSON.stringify({ status, expected_revision: ticket.revision, comment }),
      });
      onSaved();
    } catch (error) {
      setError(errorMessage(error));
      if (error instanceof ApiError && error.status === 409) setStale(true);
    } finally {
      setSaving(false);
    }
  }

  return <form className={`${form.form} ${styles.actionForm}`} onSubmit={transition}>
    <div className={form.field}>
      <label htmlFor={commentId}>Ответ студенту</label>
      <textarea id={commentId} value={comment} maxLength={500} disabled={saving || stale}
        onChange={event => setComment(event.target.value)} />
      <span className={form.hint}>При отказе укажите причину.</span>
    </div>
    <div className={styles.actions}>
      {pending ? <button value="in_progress" disabled={saving || stale}>Взять в работу</button> : <>
        <button value="ready" disabled={saving || stale}>Отметить готовой</button>
        <button value="rejected" className="button-secondary" disabled={saving || stale}>Отклонить</button>
      </>}
      {saving && <span role="status">Сохраняем…</span>}
    </div>
    {error && <div role="alert" className="notice notice-error">
      {error} {stale && <button type="button" onClick={onRefresh}>Загрузить свежую версию</button>}
    </div>}
  </form>;
}
