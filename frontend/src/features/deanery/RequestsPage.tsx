import { useRef, useState, type FormEvent } from 'react';
import { errorMessage, useApiPage } from '../../shared/academics/api';
import { api } from '../../shared/api/client';
import { Card } from '../../shared/ui/Card';
import form from '../../shared/ui/Form.module.css';
import { RolePage } from './RolePage';
import { TicketList } from './TicketList';
import { kinds, type Ticket, type TicketKind } from './tickets';

export default function RequestsPage() {
  return <RolePage role="student" title="Заявки и справки" description="Подайте заявку и следите за ответом деканата.">
    <StudentRequests />
  </RolePage>;
}

function StudentRequests() {
  const query = useApiPage<Ticket>('/requests/', { refreshEveryMs: 10_000 });
  const [kind, setKind] = useState<TicketKind>('certificate');
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const retry = useRef<{ kind: TicketKind; text: string; key: string }>(null);
  const active = useRef(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (active.current) return;
    active.current = true;
    setSaving(true);
    setError('');
    setSent(false);
    try {
      // Retrying an unchanged submission keeps its key, including after a lost response.
      const message = text.trim();
      if (retry.current?.kind !== kind || retry.current.text !== message) {
        retry.current = { kind, text: message, key: crypto.randomUUID() };
      }
      await api<Ticket>('/requests/', {
        method: 'POST',
        body: JSON.stringify({ kind, text: message, request_key: retry.current.key }),
      });
      retry.current = null;
      setText('');
      query.setPage(1);
      query.reload();
      setSent(true);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      active.current = false;
      setSaving(false);
    }
  }

  return <>
    <Card title="Новая заявка">
      <form className={form.form} onSubmit={submit}>
        <label className={form.field}>Тип заявки
          <select value={kind} disabled={saving} onChange={event => setKind(event.target.value as TicketKind)}>
            <option value="certificate">{kinds.certificate}</option>
            <option value="application">{kinds.application}</option>
          </select>
        </label>
        <div className={form.field}>
          <label htmlFor="request-text">{kind === 'application' ? 'Текст заявления' : 'Комментарий (необязательно)'}</label>
          <textarea id="request-text" value={text} maxLength={1000} required={kind === 'application'}
            disabled={saving} aria-describedby="request-help" onChange={event => setText(event.target.value)} />
          <span id="request-help" className={form.hint}>Для демонстрации используйте вымышленные данные.</span>
        </div>
        <div>{<button disabled={saving}>{saving ? 'Отправляем…' : 'Подать заявку'}</button>}</div>
        {sent && <p role="status">Заявка подана. Ответ появится в карточке заявки и уведомлениях.</p>}
        {error && <p role="alert" className="notice notice-error">{error}</p>}
      </form>
    </Card>
    <TicketList query={query} />
  </>;
}
