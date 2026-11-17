import { lazy } from 'react';
import type { AppModule } from '../../../shared/types/module';
export const academicsModule: AppModule = {
  id:'academics', path:'/academics', label:'Учёба', roles:['student'],
  Component:lazy(() => import('./AcademicsPage')),
};
