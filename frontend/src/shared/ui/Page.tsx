import type { PropsWithChildren } from 'react';
import styles from './Page.module.css';

export function Page({ title, description, children }: PropsWithChildren<{ title: string; description?: string }>) {
  return <section className={styles.page}>
    <header className={styles.heading}><h1>{title}</h1>{description && <p className={styles.lead}>{description}</p>}</header>
    {children}
  </section>;
}
