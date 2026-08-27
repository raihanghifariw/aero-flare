import type { TriageReport } from './triage-report';

export type FireStatus = 'PENDING' | 'TRIAGED' | 'ALERTED' | 'ARCHIVED';

export interface FireEvent {
  id: string;
  firms_id: string;
  detected_at: string; // ISO8601;
  lat: number;
  lon: number;
  frp: number | null; // Fire Radiative Power (MW)
  brightness: number | null; // Brightness temperature (K)
  satellite: string;
  tile_url: string | null; // Presigned R2 URL
  status: FireStatus;
  alerted_at: string | null; // ISO8601; null = not yet alerted
  created_at: string; // ISO8601
  triage?: TriageReport | null;
}

export interface FireEventsResponse {
  data: FireEvent[];
  total: number;
  page: number;
  limit: number;
}
