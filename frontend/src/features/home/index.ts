import { lazy } from 'react';
import type { AppModule } from '../../shared/types/module';

export const homeModule: AppModule = {
  id: 'home', path: '/', label: 'Главная',
  Component: lazy(() => import('./HomePage')),
};
