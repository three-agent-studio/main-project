import type { PropsWithChildren } from 'react';
import styles from './Card.module.css';

export function Card({ title, children }: PropsWithChildren<{ title: string }>) {
  return <section className={styles.card}><h2>{title}</h2>{children}</section>;
}
