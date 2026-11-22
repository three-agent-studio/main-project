import { useId, useState, type FormEvent } from 'react';
import { errorMessage, useApiPage } from '../../shared/academics/api';
import { api, ApiError } from '../../shared/api/client';
import form from '../../shared/ui/Form.module.css';
import styles from './Deanery.module.css';
import { AnnouncementForm } from './AnnouncementForm';
import { RolePage } from './RolePage';
import { TicketList } from './TicketList';
import { attachmentExtensions, maxAttachmentBytes, type Ticket } from './tickets';

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
  const [attachment, setAttachment] = useState<File | null>(null);
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
    if (attachment && attachment.size > maxAttachmentBytes) {
      setError('Файл должен быть не больше 5 МБ.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const body = new FormData();
      body.set('status', status);
      body.set('expected_revision', String(ticket.revision));
      body.set('comment', comment);
      if (attachment) body.set('attachment', attachment);
      await api<Ticket>(`/staff/requests/${ticket.id}/status/`, { method: 'POST', body });
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
      <textarea id={commentId} aria-describedby={`${commentId}-hint`} value={comment} maxLength={500} disabled={saving || stale}
        onChange={event => setComment(event.target.value)} />
      <span id={`${commentId}-hint`} className={form.hint}>Выберите действие ниже, чтобы отправить ответ. При отказе укажите причину.</span>
    </div>
    <div className={form.field}>
      <label htmlFor={`${commentId}-file`}>Приложить файл</label>
      <input id={`${commentId}-file`} className={styles.fileInput} type="file"
        accept={attachmentExtensions} disabled={saving || stale}
        aria-describedby={`${commentId}-file-help`} onChange={event => {
          setAttachment(event.currentTarget.files?.[0] ?? null);
          setError('');
        }} />
      <span id={`${commentId}-file-help`} className={form.hint}>Один PDF, PNG или JPEG до 5 МБ.</span>
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
