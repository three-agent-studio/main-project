import { Suspense, useEffect, type ComponentType } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router';
import { displayName, initials, useSession } from '../shared/api/session';
import { BoardIcon, CalendarIcon, CapIcon, DotIcon, HomeIcon, UserIcon } from '../shared/ui/icons';
import { Page } from '../shared/ui/Page';
import { modules } from './modules';
import styles from './App.module.css';

// Icons are presentation, so they stay in the shell instead of the module contract.
// A module without an entry gets a neutral dot and still works.
const moduleIcons: Record<string, ComponentType> = {
  home: HomeIcon, profile: UserIcon, academics: CalendarIcon, teaching: BoardIcon,
};

export function App() {
  const { pathname } = useLocation();
  const session = useSession();
  useEffect(() => {
    const module = modules.find((item) => item.path === pathname);
    document.title = `${module?.label ?? 'Страница не найдена'} — Цифровой деканат`;
    document.getElementById('main-content')?.focus();
  }, [pathname]);

  return <div className={styles.shell}>
    <a className="skip-link" href="#main-content">Перейти к содержимому</a>
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <Link className={styles.brand} to="/">
          <span className={styles.brandMark}><CapIcon /></span>
          <span>Цифровой деканат<span className={styles.brandCaption}>Учебная жизнь в одном месте</span></span>
        </Link>
        <div className={styles.account}>
          {session.kind === 'signed-in' && <Link className={styles.person} to="/profile">
            <span className={styles.avatar} aria-hidden="true">{initials(displayName(session.user))}</span>
            <span className={styles.personName}>{displayName(session.user)}</span>
          </Link>}
          {(session.kind === 'anonymous' || session.kind === 'error') && <a className="button" href="/auth/login/">Войти</a>}
        </div>
      </div>
    </header>
    <div className={styles.layout}>
      <nav className={styles.navigation} aria-label="Основная навигация">
        {modules.filter(module => !module.roles || (session.kind === 'signed-in'
          && module.roles.some(role => session.user.roles.includes(role))))
          .map(({ id, path, label, shortLabel }) => {
          const ModuleIcon = moduleIcons[id] ?? DotIcon;
          // Only one label is rendered visible per breakpoint; the hidden one is display:none,
          // so it never doubles the accessible name.
          return <NavLink key={id} to={path} end><ModuleIcon />
            <span className={shortLabel ? styles.longLabel : undefined}>{label}</span>
            {shortLabel && <span className={styles.shortLabel}>{shortLabel}</span>}
          </NavLink>;
        })}
      </nav>
      <main id="main-content" tabIndex={-1} className={styles.main}>
        <Suspense fallback={<p role="status">Загружаем раздел…</p>}>
          <Routes>
            {modules.map(({ id, path, Component }) => <Route key={id} path={path} element={<Component />} />)}
            <Route path="*" element={<Page title="Такой страницы нет" description="Возможно, ссылка устарела или в адресе опечатка.">
              <Link className="button" to="/">Открыть главную</Link>
            </Page>} />
          </Routes>
        </Suspense>
      </main>
    </div>
    <footer className={styles.footer}>
      <span className={styles.prototypeBadge}>Учебный проект</span>
      <span>Конкурсный прототип, не официальный сервис вуза. Все данные вымышленные.</span>
    </footer>
  </div>;
}
