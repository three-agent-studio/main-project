import { homeModule } from '../features/home';
import { profileModule } from '../features/student/profile';
import { academicsModule } from '../features/student/academics';
import { teachingModule } from '../features/teaching';
import { validateModules, type AppModule } from '../shared/types/module';

// Single integration point. Add the feature's public export, not its internal files.
export const modules: readonly AppModule[] = [homeModule, profileModule, academicsModule, teachingModule];
validateModules(modules);
