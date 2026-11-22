import { useState, type FormEvent } from 'react';
import { errorMessage } from '../../shared/academics/api';
import { api } from '../../shared/api/client';
import { Card } from '../../shared/ui/Card';
import form from '../../shared/ui/Form.module.css';

export function AnnouncementForm() {
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: 'error' | 'success'; message: string }>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setStatus(undefined);
    try {
      await api('/staff/announcements/', { method: 'POST', body: JSON.stringify({ title, message }) });
      setTitle('');
      setMessage('');
      setStatus({ type: 'success', message: 'Объявление опубликовано для вашего факультета.' });
    } catch (error) {
      setStatus({ type: 'error', message: errorMessage(error) });
    } finally {
      setSaving(false);
    }
  }
  return <Card title="Объявление для факультета">
    <details>
      <summary>Написать объявление</summary>
      <form className={form.form} onSubmit={submit}>
        <label className={form.field}>Заголовок
          <input required maxLength={180} value={title} disabled={saving}
            onChange={event => setTitle(event.target.value)} />
        </label>
        <label className={form.field}>Текст объявления
          <textarea required maxLength={1500} value={message} disabled={saving}
            onChange={event => setMessage(event.target.value)} />
        </label>
        <div><button disabled={saving}>{saving ? 'Публикуем…' : 'Опубликовать'}</button></div>
        {status && <p role={status.type === 'error' ? 'alert' : 'status'}>{status.message}</p>}
      </form>
    </details>
  </Card>;
}
