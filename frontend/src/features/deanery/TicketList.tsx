import type { ReactNode } from 'react';
import { dateLabel, useApiPage } from '../../shared/academics/api';
import { Pagination } from '../../shared/academics/Pagination';
import { Badge } from '../../shared/ui/Badge';
import { Card } from '../../shared/ui/Card';
import { EmptyState } from '../../shared/ui/EmptyState';
import { kinds, statuses, tones, type Ticket } from './tickets';
import styles from './Deanery.module.css';

export type TicketQuery = ReturnType<typeof useApiPage<Ticket>>;

export function TicketList({ query, staff = false, action }: {
  query: TicketQuery; staff?: boolean; action?: (ticket: Ticket) => ReactNode;
}) {
  return <Card title={staff ? 'Заявки факультета' : 'Мои заявки'}>
    {query.loading && <p role="status">Загружаем заявки…</p>}
    {query.error && <div className="notice notice-error" role="alert">
      {query.error} <button onClick={query.reload}>Обновить список</button>
    </div>}
    {query.data?.count === 0 && <EmptyState title="Заявок пока нет" />}
    {query.data?.results.map(ticket => <article className={styles.entry} key={ticket.id}>
      <div className={styles.heading}>
        <h3>{kinds[ticket.kind]}</h3>
        <Badge tone={tones[ticket.status]}>{statuses[ticket.status]}</Badge>
      </div>
      <p className={styles.meta}>{staff && <>{ticket.student_name} · </>}{dateLabel(ticket.created_at)}</p>
      {ticket.text && <p>{ticket.text}</p>}
      <details className={styles.details}>
        <summary>История заявки ({ticket.history.length})</summary>
        <ol className={styles.timeline} aria-label="История статусов">
          {ticket.history.map(event => <li key={event.revision}>
            <strong>{statuses[event.status]}</strong>
            <time dateTime={event.created_at} className={styles.meta}>{dateLabel(event.created_at)}</time>
            {event.comment && <p>{event.comment}</p>}
          </li>)}
        </ol>
      </details>
      {action?.(ticket)}
    </article>)}
    {query.data && <Pagination data={query.data} page={query.page} setPage={query.setPage} />}
  </Card>;
}
