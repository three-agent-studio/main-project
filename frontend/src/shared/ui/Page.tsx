import type { PropsWithChildren } from 'react';

export function Page({ title, description, children }: PropsWithChildren<{ title: string; description?: string }>) {
  return <section><h1>{title}</h1>{description && <p>{description}</p>}{children}</section>;
}
