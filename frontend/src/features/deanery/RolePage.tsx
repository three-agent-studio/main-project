import type { ReactNode } from 'react';
import { useSession } from '../../shared/api/session';
import { Page } from '../../shared/ui/Page';

export function RolePage({ role, title, description, children }: {
  role: 'student' | 'deanery_staff'; title: string; description: string; children: ReactNode;
}) {
  const session = useSession();
  return <Page title={title} description={description}>
    {session.kind === 'loading' && <p role="status">Проверяем доступ…</p>}
    {session.kind === 'error' && <div role="alert" className="notice notice-error">
      Не удалось проверить сеанс. <button onClick={() => window.location.reload()}>Повторить</button>
    </div>}
    {session.kind === 'anonymous' && <a className="button" href="/auth/login/">Войти в кабинет</a>}
    {session.kind === 'signed-in' && (session.user.roles.includes(role)
      ? children : <p>Раздел доступен только {role === 'student' ? 'студентам' : 'сотрудникам деканата'}.</p>)}
  </Page>;
}
