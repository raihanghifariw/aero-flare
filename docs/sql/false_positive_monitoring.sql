-- ============================================================
-- Aero-Flare: False Positive Rate Monitoring
-- Run weekly in Supabase SQL Editor to track VLM triage quality.
-- Target: fp_rate_pct < 15% per week (PRD Section 5 success metric)
-- ============================================================

-- ─── 1. Weekly false positive rate (last 8 weeks) ────────────────────────────
SELECT
    DATE_TRUNC('week', processed_at) AS week,
    COUNT(*) FILTER (WHERE classification = 'FALSE_POSITIVE')   AS false_positives,
    COUNT(*) FILTER (WHERE classification = 'CONFIRMED_FIRE')   AS confirmed_fires,
    COUNT(*) FILTER (WHERE classification = 'PROBABLE_FIRE')    AS probable_fires,
    COUNT(*) FILTER (WHERE classification = 'INDUSTRIAL_SOURCE') AS industrial,
    COUNT(*)                                                     AS total,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE classification = 'FALSE_POSITIVE') / NULLIF(COUNT(*), 0),
        1
    ) AS fp_rate_pct
FROM triage_reports
WHERE processed_at >= NOW() - INTERVAL '8 weeks'
GROUP BY 1
ORDER BY 1 DESC;

-- ─── 2. Triage source breakdown (VLM vs rule-based) ──────────────────────────
SELECT
    triage_source,
    COUNT(*) AS total,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM triage_reports
GROUP BY triage_source
ORDER BY total DESC;

-- ─── 3. Average confidence by classification ─────────────────────────────────
SELECT
    classification,
    COUNT(*)             AS count,
    ROUND(AVG(confidence)::numeric, 3) AS avg_confidence,
    ROUND(MIN(confidence)::numeric, 3) AS min_confidence,
    ROUND(MAX(confidence)::numeric, 3) AS max_confidence
FROM triage_reports
GROUP BY classification
ORDER BY count DESC;

-- ─── 4. Alert: flag if FP rate > 15% in the current week ─────────────────────
SELECT
    CASE
        WHEN ROUND(
            100.0 * COUNT(*) FILTER (WHERE classification = 'FALSE_POSITIVE')
            / NULLIF(COUNT(*), 0), 1
        ) > 15 THEN '🚨 FP RATE > 15% — REVIEW PROMPT'
        ELSE '✅ FP rate within target'
    END AS alert_status,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE classification = 'FALSE_POSITIVE')
        / NULLIF(COUNT(*), 0), 1
    ) AS fp_rate_pct
FROM triage_reports
WHERE processed_at >= DATE_TRUNC('week', NOW());
