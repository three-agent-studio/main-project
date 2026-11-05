import { Suspense, useEffect } from 'react';
import { NavLink, Route, Routes, useLocation } from 'react-router';
import { Page } from '../shared/ui/Page';
import { modules } from './modules';
import styles from './App.module.css';

export function App() {
  const { pathname } = useLocation();
  useEffect(() => {
    const module = modules.find((item) => item.path === pathname);
    document.title = `${module?.label ?? 'Страница не найдена'} — Цифровой деканат`;
    document.getElementById('main-content')?.focus();
  }, [pathname]);

  return <>
    <a className="skip-link" href="#main-content">Перейти к содержимому</a>
    <header className={styles.header}>
      <NavLink className={styles.brand} to="/">Цифровой деканат<span>Учебная жизнь в одном месте</span></NavLink>
      <a className="button" href="/auth/login/">Войти</a>
    </header>
    <div className={styles.layout}>
      <nav className={styles.navigation} aria-label="Основная навигация">
        {modules.map(({ id, path, label }) => <NavLink key={id} to={path} end>{label}</NavLink>)}
      </nav>
      <main id="main-content" tabIndex={-1} className={styles.main}>
        <Suspense fallback={<p role="status">Загрузка раздела…</p>}>
          <Routes>
            {modules.map(({ id, path, Component }) => <Route key={id} path={path} element={<Component />} />)}
            <Route path="*" element={<Page title="Страница не найдена"><NavLink to="/">На главную</NavLink></Page>} />
          </Routes>
        </Suspense>
      </main>
    </div>
    <footer className={styles.footer}>Конкурсный прототип. Не официальный сервис вуза. Только вымышленные данные.</footer>
  </>;
}
