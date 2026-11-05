import { expect, it } from 'vitest';
import { validateModules } from './module';

it('rejects conflicting routes before rendering the navigation', () => {
  const module = { id: 'one', path: '/', label: 'One', Component: () => null };
  expect(() => validateModules([module, { ...module, id: 'two' }])).toThrow('Duplicate module path');
});
