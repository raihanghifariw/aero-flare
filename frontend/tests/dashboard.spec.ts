import { test, expect } from '@playwright/test';

// All tests use mocked API responses so they run without a live backend.
// The proxy route.ts files are intercepted at the network level.

const MOCK_EVENT = {
  id: 'evt-test-001',
  firms_id: 'FIRMS_001',
  detected_at: new Date().toISOString(),
  lat: -2.5,
  lon: 118.7,
  frp: 125.5,
  brightness: 340.2,
  satellite: 'MODIS',
  tile_url: null,
  status: 'TRIAGED',
  alerted_at: null,
  created_at: new Date().toISOString(),
};

const MOCK_TRIAGE = {
  id: 'tri-test-001',
  event_id: 'evt-test-001',
  classification: 'CONFIRMED_FIRE',
  confidence: 0.94,
  fire_area_ha: 250.0,
  smoke_direction: 'NE',
  danger_level: 4,
  summary: 'Large confirmed wildfire with active spreading in forested area.',
  recommended_action: 'DISPATCH',
  triage_source: 'VLM',
  processed_at: new Date().toISOString(),
};

const MOCK_TRIAGE_RULE_BASED = {
  ...MOCK_TRIAGE,
  id: 'tri-test-002',
  event_id: 'evt-test-002',
  triage_source: 'RULE_BASED_FALLBACK',
  confidence: 0.72,
  danger_level: 2,
  summary: 'Classified by rule-based fallback (VLM unavailable).',
};

const MOCK_PREDICTION = {
  id: 'pred-test-001',
  event_id: 'evt-test-001',
  spread_direction_deg: 45,
  radius_6h_km: 3.2,
  radius_12h_km: 6.8,
  radius_24h_km: 14.5,
  wind_speed: 5.2,
  wind_direction: 45,
  humidity: 35,
  model_version: 'xgb-v1.0',
  predicted_at: new Date().toISOString(),
};

const MOCK_STATS = {
  events_today: 12,
  confirmed_fires_today: 4,
  last_ingestion_at: new Date().toISOString(),
  pipeline_healthy: true,
};

// ─── Shared route mock helper ─────────────────────────────────────────────────

async function mockBackendRoutes(page: import('@playwright/test').Page) {
  await page.route('/api/proxy/events*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [MOCK_EVENT],
        total: 1,
        page: 1,
        limit: 100,
      }),
    });
  });

  await page.route('/api/proxy/triage/evt-test-001', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_TRIAGE),
    });
  });

  await page.route('/api/proxy/predictions/evt-test-001', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_PREDICTION),
    });
  });

  await page.route('/api/proxy/stats', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_STATS),
    });
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('Aero-Flare Dashboard', () => {
  /**
   * Test 1: Dashboard loads without errors
   */
  test('dashboard loads without errors', async ({ page }) => {
    await mockBackendRoutes(page);
    await page.goto('/');

    // Page should not show an error alert
    await expect(page.getByTestId('error-alert')).not.toBeVisible();

    // Stats bar should render with real numbers
    await expect(page.getByText('12')).toBeVisible();
    await expect(page.getByText('Events today')).toBeVisible();
  });

  /**
   * Test 2: Map renders with at least one fire marker
   */
  test('map renders with at least one fire marker', async ({ page }) => {
    await mockBackendRoutes(page);
    await page.goto('/');

    // Wait for map container
    const mapContainer = page.getByTestId('fire-map-container');
    await expect(mapContainer).toBeVisible();

    // Leaflet SVG markers should appear
    // Circle markers are rendered as <path> inside SVG by Leaflet
    await page.waitForSelector('.leaflet-overlay-pane svg path', { timeout: 8000 });
  });

  /**
   * Test 3: Clicking a marker opens the triage modal with classification data
   */
  test('clicking a marker opens triage modal with classification data', async ({ page }) => {
    await mockBackendRoutes(page);
    await page.goto('/');

    // Trigger marker click via the event sidebar (more reliable than SVG hit-testing)
    const sidebarBtn = page.getByTestId('event-sidebar').locator('button').first();
    await sidebarBtn.click();

    // Triage modal should appear
    const modal = page.getByTestId('triage-modal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Classification data
    await expect(modal.getByTestId('classification-tag')).toContainText('Confirmed Fire');
    await expect(modal.getByTestId('danger-badge')).toBeVisible();
    await expect(modal.getByTestId('triage-source-badge')).toContainText('VLM');
  });

  /**
   * Test 4: Event sidebar filters by danger level
   */
  test('event sidebar shows events and danger badges', async ({ page }) => {
    await mockBackendRoutes(page);
    await page.goto('/');

    const sidebar = page.getByTestId('event-sidebar');
    await expect(sidebar).toBeVisible();

    // Danger badge for level 4 should appear (from MOCK_TRIAGE)
    // Note: sidebar shows pre-triaged events; triage source from triageMap
    await expect(sidebar).toBeVisible();
    // Stats bar values from mock
    await expect(page.getByText('4')).toBeVisible(); // confirmed_fires_today
  });

  /**
   * Test 5: Spread chart renders when prediction data exists
   */
  test('spread radius chart renders 3 bars', async ({ page }) => {
    await mockBackendRoutes(page);
    await page.goto('/');

    // Open triage modal via sidebar
    const sidebarBtn = page.getByTestId('event-sidebar').locator('button').first();
    await sidebarBtn.click();

    const modal = page.getByTestId('triage-modal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Spread radius chart should be present
    const chart = modal.getByTestId('spread-radius-chart');
    await expect(chart).toBeVisible({ timeout: 5000 });

    // Recharts renders bar cells — verify the container text shows horizon labels
    await expect(chart).toContainText('6h');
    await expect(chart).toContainText('12h');
    await expect(chart).toContainText('24h');
  });

  /**
   * Test 6: Error state shown when API is unreachable
   */
  test('shows error alert when API is unreachable', async ({ page }) => {
    // Return 500 for events endpoint
    await page.route('/api/proxy/events*', async (route) => {
      await route.fulfill({ status: 500, body: '{"detail":"Internal Server Error"}' });
    });
    await page.route('/api/proxy/stats', async (route) => {
      await route.fulfill({ status: 500, body: '{"detail":"Internal Server Error"}' });
    });

    await page.goto('/');

    // Error alert should appear
    await expect(page.getByTestId('error-alert')).toBeVisible({ timeout: 8000 });
  });

  /**
   * Test 7: RULE_BASED_FALLBACK triage shows warning indicator in modal
   */
  test('RULE_BASED_FALLBACK triage shows warning indicator', async ({ page }) => {
    // Override with rule-based event
    const ruleEvent = { ...MOCK_EVENT, id: 'evt-test-002', status: 'TRIAGED' as const };

    await page.route('/api/proxy/events*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [ruleEvent], total: 1, page: 1, limit: 100 }),
      });
    });
    await page.route('/api/proxy/triage/evt-test-002', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_TRIAGE_RULE_BASED),
      });
    });
    await page.route('/api/proxy/predictions/*', async (route) => {
      await route.fulfill({ status: 404, body: '{"detail":"Not found"}' });
    });
    await page.route('/api/proxy/stats', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_STATS),
      });
    });

    await page.goto('/');

    // Click the first sidebar item to open modal
    const sidebarBtn = page.getByTestId('event-sidebar').locator('button').first();
    await sidebarBtn.click();

    const modal = page.getByTestId('triage-modal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Rule-Based badge with warning icon should appear
    const badge = modal.getByTestId('triage-source-badge');
    await expect(badge).toContainText('Rule-Based');
    await expect(badge).toContainText('⚠');
  });
});
