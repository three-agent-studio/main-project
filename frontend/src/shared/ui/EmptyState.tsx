import type { PropsWithChildren, ReactNode } from 'react';
import styles from './EmptyState.module.css';

/** What this is, why it is empty and, when there is one, the next action. */
export function EmptyState({ title, action, children }: PropsWithChildren<{ title: string; action?: ReactNode }>) {
  return <div className={styles.empty}>
    <p className={styles.title}>{title}</p>
    {children && <p className={styles.text}>{children}</p>}
    {action}
  </div>;
}
