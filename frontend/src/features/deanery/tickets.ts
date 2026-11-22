import type { BadgeTone } from '../../shared/ui/Badge';

export const kinds = { certificate: 'Справка об обучении', application: 'Заявление в деканат' };
export const statuses = {
  submitted: 'Подана', in_progress: 'В работе', ready: 'Готова', rejected: 'Отклонена',
};
export type TicketKind = keyof typeof kinds;
export type TicketStatus = keyof typeof statuses;
export const tones: Record<TicketStatus, BadgeTone> = {
  submitted: 'neutral', in_progress: 'info', ready: 'success', rejected: 'danger',
};
export interface Ticket {
  id: string;
  kind: TicketKind;
  student_name: string;
  text: string;
  status: TicketStatus;
  revision: number;
  created_at: string;
  history: {status: TicketStatus; revision: number; comment: string; created_at: string}[];
}
