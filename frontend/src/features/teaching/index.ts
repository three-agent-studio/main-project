import { lazy } from 'react';
import type { AppModule } from '../../shared/types/module';

export const teachingModule: AppModule = {
  id: 'teaching', path: '/teaching', label: 'Кабинет преподавателя', shortLabel: 'Преподавание', roles: ['teacher'],
  Component: lazy(() => import('./TeachingPage')),
};
