import { Component, type PropsWithChildren } from 'react';

export class ErrorBoundary extends Component<PropsWithChildren, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <main style={{ padding: 24, maxWidth: 640 }}>
      <h1>Не удалось открыть страницу</h1><p role="alert" className="notice notice-error">При загрузке произошла ошибка. Обновите страницу, чтобы продолжить.</p>
      <button onClick={() => window.location.reload()}>Обновить</button>
    </main>;
    return this.props.children;
  }
}
