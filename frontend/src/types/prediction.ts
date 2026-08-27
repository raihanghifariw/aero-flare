// TypeScript types mirroring backend Pydantic schemas
// Kept in sync with: backend/app/schemas/prediction.py

export interface Prediction {
  id: string;
  event_id: string;
  spread_direction_deg: number; // 0–360
  radius_6h_km: number;
  radius_12h_km: number;
  radius_24h_km: number;
  wind_speed: number; // m/s
  wind_direction: number; // degrees
  humidity: number; // percentage 0–100
  model_version: string;
  predicted_at: string; // ISO8601
}
