import type { PropsWithChildren } from 'react';
import styles from './Badge.module.css';

/** Status label. Tone only reinforces the text; the words must carry the meaning on
 *  their own (colour-blind users, screen readers). Suggested mapping for requests (#8):
 *  Подана → neutral, В работе → info, Готова → success, Отклонена → danger. */
export type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export function Badge({ tone = 'neutral', children }: PropsWithChildren<{ tone?: BadgeTone }>) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
