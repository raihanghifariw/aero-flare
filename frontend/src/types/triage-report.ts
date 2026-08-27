// TypeScript types mirroring backend Pydantic schemas
// Kept in sync with: backend/app/schemas/triage_report.py

export type Classification =
  | 'CONFIRMED_FIRE'
  | 'PROBABLE_FIRE'
  | 'FALSE_POSITIVE'
  | 'INDUSTRIAL_SOURCE';

export type RecommendedAction = 'MONITOR' | 'DISPATCH' | 'EVACUATE';

// 'VLM' = classified by Vision Language Model
// 'RULE_BASED_FALLBACK' = VLM unavailable; rule-based classifier used instead
export type TriageSource = 'VLM' | 'RULE_BASED_FALLBACK';

export interface TriageReport {
  id: string;
  event_id: string;
  classification: Classification;
  confidence: number; // 0.0–1.0
  fire_area_ha: number | null;
  smoke_direction: string | null;
  cloud_cover_percent?: number | null;
  visually_obscured?: boolean | null;
  danger_level: number; // 1–5
  summary: string;
  recommended_action: RecommendedAction;
  triage_source: TriageSource; // 'VLM' | 'RULE_BASED_FALLBACK'
  processed_at: string; // ISO8601
}
