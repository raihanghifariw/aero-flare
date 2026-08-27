// TypeScript types mirroring backend Pydantic schemas
// Kept in sync with: backend/app/schemas/fire_event.py

export type FireStatus = 'PENDING' | 'TRIAGED' | 'ALERTED' | 'ARCHIVED';

export interface FireEvent {
  id: string;
  firms_id: string;
  detected_at: string; // ISO8601
  lat: number;
  lon: number;
  frp: number | null; // Fire Radiative Power (MW)
  brightness: number | null; // Brightness temperature (K)
  satellite: string;
  tile_url: string | null; // Presigned R2 URL
  status: FireStatus;
  alerted_at: string | null; // ISO8601; null = not yet alerted
  created_at: string; // ISO8601
}

export interface FireEventsResponse {
  data: FireEvent[];
  total: number;
  page: number;
  limit: number;
}
