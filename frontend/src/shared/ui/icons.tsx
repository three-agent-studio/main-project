import type { SVGProps } from 'react';

/* Line icons drawn for this project (24px grid, 1.8 stroke). Decorative by default:
   the visible label next to an icon always carries the meaning. */
type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps) {
  return <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}>{children}</svg>;
}

export const HomeIcon = (p: IconProps) => <Icon {...p}><path d="M4 11.5 12 5l8 6.5" /><path d="M6.5 10v9h11v-9" /><path d="M10 19v-5h4v5" /></Icon>;
export const UserIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="8.5" r="3.5" /><path d="M5 19.5c1.2-3.3 3.8-5 7-5s5.8 1.7 7 5" /></Icon>;
export const CalendarIcon = (p: IconProps) => <Icon {...p}><rect x="4" y="5.5" width="16" height="14" rx="3" /><path d="M8 3.5v4M16 3.5v4M4 10.5h16" /></Icon>;
export const GradesIcon = (p: IconProps) => <Icon {...p}><path d="M6 4.5h9l3 3v12H6z" /><path d="M9 12.5l2 2 4-4.5" /></Icon>;
export const RequestIcon = (p: IconProps) => <Icon {...p}><path d="M7 3.5h7l4 4v13H7z" /><path d="M14 3.5v4h4M10 12h5M10 15.5h5" /></Icon>;
export const BellIcon = (p: IconProps) => <Icon {...p}><path d="M6.5 10a5.5 5.5 0 0 1 11 0c0 5 2 6 2 6.5h-15c0-.5 2-1.5 2-6.5" /><path d="M10 19.5a2.2 2.2 0 0 0 4 0" /></Icon>;
export const DotIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="12" r="3" /></Icon>;
export const CapIcon = (p: IconProps) => <Icon {...p}><path d="m3 9.5 9-4.5 9 4.5-9 4.5z" /><path d="M7 11.5v4.5c3 2.2 7 2.2 10 0v-4.5M21 9.5v5.5" /></Icon>;
