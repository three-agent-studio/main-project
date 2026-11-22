import { lazy } from 'react';
import type { AppModule } from '../../shared/types/module';

export const requestsModule: AppModule = {
  id: 'requests', path: '/requests', label: 'Заявки', roles: ['student'],
  Component: lazy(() => import('./RequestsPage')),
};
export const notificationsModule: AppModule = {
  id: 'notifications', path: '/notifications', label: 'Уведомления', shortLabel: 'Новости', roles: ['student'],
  Component: lazy(() => import('./NotificationsPage')),
};
export const staffModule: AppModule = {
  id: 'deanery', path: '/deanery', label: 'Кабинет деканата', shortLabel: 'Деканат', roles: ['deanery_staff'],
  Component: lazy(() => import('./StaffPage')),
};
