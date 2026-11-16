import type { ApiPage } from './api';
import styles from './Study.module.css';

export function Pagination({ data, page, setPage }: {
  data: ApiPage<unknown>; page: number; setPage: (page: number) => void;
}) {
  return <div className={styles.pagination} aria-label="Страницы списка">
    <span>Всего: {data.count}. Страница {page}</span>
    <button type="button" className="button-secondary" disabled={!data.previous}
      onClick={() => setPage(page - 1)}>Назад</button>
    <button type="button" className="button-secondary" disabled={!data.next}
      onClick={() => setPage(page + 1)}>Далее</button>
  </div>;
}
