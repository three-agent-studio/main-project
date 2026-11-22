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
export const maxAttachmentBytes = 5 * 1024 * 1024;
export const attachmentExtensions = '.pdf,.png,.jpg,.jpeg';

export interface TicketEvent {
  id: string;
  status: TicketStatus;
  revision: number;
  comment: string;
  created_at: string;
  attachment: null | {filename: string; size: number};
}

export interface Ticket {
  id: string;
  kind: TicketKind;
  student_name: string;
  text: string;
  status: TicketStatus;
  revision: number;
  created_at: string;
  history: TicketEvent[];
}
