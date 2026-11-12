import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './app/App';
import { ErrorBoundary } from './shared/ui/ErrorBoundary';
import '@fontsource-variable/onest';
import './shared/styles/tokens.css';
import './shared/styles/global.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode><ErrorBoundary><BrowserRouter><App /></BrowserRouter></ErrorBoundary></StrictMode>,
);
