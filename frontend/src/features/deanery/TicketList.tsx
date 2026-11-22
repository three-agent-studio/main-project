import type { ReactNode } from 'react';
import { dateLabel, type useApiPage } from '../../shared/academics/api';
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
    {!staff && <div className={styles.refresh}>
      <button className="button-secondary" onClick={query.reload}>Обновить статусы</button>
    </div>}
    {query.loading && <p role="status">Загружаем заявки…</p>}
    {query.error && <div className="notice notice-error" role="alert">
      {query.error} {staff && <button onClick={query.reload}>Обновить список</button>}
    </div>}
    {query.data?.count === 0 && <EmptyState title="Заявок пока нет" />}
    {query.data?.results.map(ticket => <TicketEntry key={ticket.id} ticket={ticket} staff={staff}>
      {action?.(ticket)}
    </TicketEntry>)}
    {query.data && <Pagination data={query.data} page={query.page} setPage={query.setPage} />}
  </Card>;
}


function TicketEntry({ ticket, staff, children }: {
  ticket: Ticket; staff: boolean; children?: ReactNode;
}) {
  // Keep the most recent non-empty reply visible even if a later status has no comment.
  const reply = staff ? undefined : [...ticket.history].reverse().find(event => event.comment.trim());
  return <article className={styles.entry}>
    <div className={styles.heading}>
      <h3>{kinds[ticket.kind]}</h3>
      <span aria-live={staff ? undefined : 'polite'}>
        <Badge tone={tones[ticket.status]}>{statuses[ticket.status]}</Badge>
      </span>
    </div>
    <p className={styles.meta}>{staff && <>{ticket.student_name} · </>}{dateLabel(ticket.created_at)}</p>
    {ticket.text && <p>{ticket.text}</p>}
    {reply && <section className={styles.reply} aria-label="Ответ деканата">
      <strong>Ответ деканата</strong>
      <time className={styles.meta} dateTime={reply.created_at}>{dateLabel(reply.created_at)}</time>
      <p>{reply.comment}</p>
    </section>}
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
    {children}
  </article>;
}
