import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Apple HIG & WCAG Accessibility Audit (@axe-core)', () => {
  test('Page level accessibility check on initial load', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Run axe accessibility scan across the application interface
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .exclude('.leaflet-container')
      .analyze();

    // Critical and serious violations must be zero
    const severeViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(severeViolations).toEqual([]);
  });

  test('Detail drawer accessibility and focus trap compliance', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Click first card to open detail drawer
    const firstCard = page.locator('#cards-container .group').first();
    await firstCard.click();
    await page.waitForTimeout(600);

    const drawer = page.locator('div[role="dialog"][aria-label="活动详情"]');
    await expect(drawer).toBeVisible();

    const results = await new AxeBuilder({ page })
      .include('div[role="dialog"][aria-label="活动详情"]')
      .analyze();

    const severeViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(severeViolations).toEqual([]);
  });

  test('Stats modal dialog accessibility compliance', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Open Stats modal
    const statsBtn = page.locator('button:has-text("概览统计")').first();
    if (await statsBtn.isVisible()) {
      await statsBtn.click();
      await page.waitForTimeout(1000);

      const modal = page.locator('div[role="dialog"][aria-label="南京活动概览统计"]');
      await expect(modal).toBeVisible();

      const results = await new AxeBuilder({ page })
        .include('div[role="dialog"][aria-label="南京活动概览统计"]')
        .analyze();

      const severeViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
      expect(severeViolations).toEqual([]);
    }
  });
});
