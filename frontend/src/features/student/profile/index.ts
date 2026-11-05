import { lazy } from 'react';
import type { AppModule } from '../../../shared/types/module';

export const profileModule: AppModule = {
  id: 'profile', path: '/profile', label: 'Мой профиль',
  Component: lazy(() => import('./ProfilePage')),
};
