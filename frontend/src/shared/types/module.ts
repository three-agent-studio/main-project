import type { ComponentType } from 'react';

/** Each feature owns its pages; the app only composes exported module descriptors. */
export interface AppModule {
  id: string;
  path: string;
  label: string;
  /** Optional short name for the phone tab bar, where width is tight. */
  shortLabel?: string;
  Component: ComponentType;
  /** Navigation visibility only. Every API still checks the role and data scope. */
  roles?: readonly string[];
}

export function validateModules(modules: readonly AppModule[]): void {
  for (const key of ['id', 'path'] as const) {
    if (new Set(modules.map((module) => module[key])).size !== modules.length) {
      throw new Error(`Duplicate module ${key}`);
    }
  }
}
