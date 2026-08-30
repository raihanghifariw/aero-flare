import { test } from '@playwright/test';
import path from 'path';

const MOCK_EVENT = {
  id: 'evt-test-001',
  firms_id: 'FIRMS_001',
  detected_at: new Date().toISOString(),
  lat: -0.789,
  lon: 113.921,
  frp: 185.4,
  brightness: 342.5,
  satellite: 'SNPP-VIIRS',
  tile_url: null,
  status: 'TRIAGED',
  alerted_at: null,
  created_at: new Date().toISOString(),
};

const MOCK_TRIAGE = {
  id: 'tri-test-001',
  event_id: 'evt-test-001',
  classification: 'CONFIRMED_FIRE',
  confidence: 0.96,
  fire_area_ha: 320.0,
  smoke_direction: 'NE',
  danger_level: 4,
  summary: 'Active crown fire spreading rapidly along peat forest canopy with intense thermal signature.',
  recommended_action: 'DISPATCH',
  triage_source: 'VLM',
  processed_at: new Date().toISOString(),
};

const MOCK_PREDICTION = {
  id: 'pred-test-001',
  event_id: 'evt-test-001',
  spread_direction_deg: 45,
  radius_6h_km: 4.2,
  radius_12h_km: 8.5,
  radius_24h_km: 18.2,
  wind_speed: 18.5,
  wind_direction: 45,
  humidity: 32,
  model_version: 'xgb-v1.0',
  predicted_at: new Date().toISOString(),
};

const MOCK_STATS = {
  events_today: 48,
  confirmed_fires_today: 14,
  last_ingestion_at: new Date().toISOString(),
  pipeline_healthy: true,
};

test.describe('Visual Verification Screenshots', () => {
  test('capture redesigned screens', async ({ page }) => {
    // Intercept routes
    await page.route('**/api/proxy/events*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            MOCK_EVENT,
            { ...MOCK_EVENT, id: 'evt-test-002', lat: -2.12, lon: 115.34, frp: 92.1, status: 'ALERTED' },
            { ...MOCK_EVENT, id: 'evt-test-003', lat: 0.45, lon: 101.89, frp: 45.0, status: 'TRIAGED' },
          ],
          total: 3,
          page: 1,
          limit: 100,
        }),
      });
    });

    await page.route('**/api/proxy/events/evt-test-001', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...MOCK_EVENT,
          triage: MOCK_TRIAGE,
          prediction: MOCK_PREDICTION,
        }),
      });
    });

    await page.route('**/api/proxy/triage/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_TRIAGE),
      });
    });

    await page.route('**/api/proxy/predictions/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_PREDICTION),
      });
    });

    await page.route('**/api/proxy/stats', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_STATS),
      });
    });

    const artifactsDir = 'C:\\Users\\DELL\\.gemini\\antigravity-ide\\brain\\050aceb8-80ab-4a14-a0b7-d52ab5ccbf3a';

    // 1. Dashboard View
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(artifactsDir, 'dashboard_redesign.png') });

    // 2. Triage Drawer Opened
    const sidebarBtn = page.getByTestId('event-sidebar').locator('button').first();
    await sidebarBtn.click();
    await page.waitForSelector('[data-testid="triage-modal"]');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(artifactsDir, 'triage_drawer_redesign.png') });

    // 3. Incidents Explorer
    await page.goto('/events');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(artifactsDir, 'incidents_explorer_redesign.png') });

    // 4. Incident Detail View
    await page.goto('/events/evt-test-001');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(artifactsDir, 'incident_detail_redesign.png') });
  });
});
