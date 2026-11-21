import type { ApiPage } from './api';
import styles from './Study.module.css';

export function Pagination({ data, page, setPage }: {
  data: ApiPage<unknown>; page: number; setPage: (page: number) => void;
}) {
  // A single page needs no controls: the whole list is already on screen.
  if (!data.previous && !data.next) return null;
  return <nav className={styles.pagination} aria-label="Страницы списка">
    <span>Всего: {data.count}. Страница {page}</span>
    <div>
      <button type="button" className="button-secondary" disabled={!data.previous}
        onClick={() => setPage(page - 1)}>Назад</button>
      <button type="button" className="button-secondary" disabled={!data.next}
        onClick={() => setPage(page + 1)}>Далее</button>
    </div>
  </nav>;
}
