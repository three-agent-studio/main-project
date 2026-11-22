import { useState } from 'react';
import { Link } from 'react-router';
import { dateLabel, errorMessage, useApiPage } from '../../shared/academics/api';
import { Pagination } from '../../shared/academics/Pagination';
import { api } from '../../shared/api/client';
import { Badge } from '../../shared/ui/Badge';
import { Card } from '../../shared/ui/Card';
import { EmptyState } from '../../shared/ui/EmptyState';
import styles from './Deanery.module.css';
import { RolePage } from './RolePage';

const categories = {
  news: 'Деканат', schedule: 'Расписание', request: 'Заявка', deadline: 'Дедлайн',
};
type Category = keyof typeof categories;
interface Notice {
  key: string; category: Category; headline: string; body: string; occurred_at: string; read: boolean;
}

export default function NotificationsPage() {
  return <RolePage role="student" title="Уведомления" description="Объявления, изменения расписания, ответы по заявкам и ближайшие сроки.">
    <NoticeList />
  </RolePage>;
}

function NoticeList() {
  const query = useApiPage<Notice>('/notifications/');
  return <Card title="Лента">
    {query.loading && <p role="status">Загружаем уведомления…</p>}
    {query.error && <div role="alert" className="notice notice-error">
      {query.error} <button onClick={query.reload}>Повторить</button>
    </div>}
    {query.data?.count === 0 && <EmptyState title="Уведомлений пока нет" />}
    {query.data?.results.map(notice => <NoticeEntry key={notice.key} notice={notice} />)}
    {query.data && <Pagination data={query.data} page={query.page} setPage={query.setPage} />}
  </Card>;
}

function NoticeEntry({ notice }: { notice: Notice }) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const read = notice.read || saved;
  async function markRead() {
    setSaving(true);
    setError('');
    try {
      await api<void>(`/notifications/${encodeURIComponent(notice.key)}/read/`, { method: 'POST' });
      setSaved(true);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }
  return <article className={styles.entry}>
    <div className={styles.actions}>
      <Badge>{categories[notice.category]}</Badge>
      <Badge tone={read ? 'neutral' : 'info'}>{read ? 'Прочитано' : 'Новое'}</Badge>
    </div>
    <h3>{notice.headline}</h3>
    <p className={styles.meta}>{notice.category === 'deadline' ? 'Срок сдачи: ' : ''}{dateLabel(notice.occurred_at)}</p>
    {notice.body && <p>{notice.body}</p>}
    <div className={styles.actions}>
      {!read && <button className="button-secondary" disabled={saving} onClick={markRead}>
        {saving ? 'Сохраняем…' : 'Отметить прочитанным'}
      </button>}
      {notice.category === 'request' && <Link to="/requests">Мои заявки</Link>}
      {(notice.category === 'schedule' || notice.category === 'deadline') && <Link to="/academics">Открыть «Учёбу»</Link>}
    </div>
    {error && <p role="alert" className="notice notice-error">{error}</p>}
  </article>;
}
