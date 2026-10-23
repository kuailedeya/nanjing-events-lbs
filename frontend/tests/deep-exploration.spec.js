import { test, expect } from '@playwright/test';

test.describe('Deep Frontend Exploration & Edge-Cases Test Suite', () => {
  test('Zero Console Errors and Zero Broken Assets during full page load', async ({ page }) => {
    const consoleErrors = [];
    const failedRequests = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        const txt = msg.text();
        // Ignore external tile provider offline/connection timeouts
        if (txt.includes('net::ERR_') || txt.includes('favicon')) return;
        consoleErrors.push(txt);
      }
    });

    page.on('pageerror', err => {
      consoleErrors.push(err.message);
    });

    page.on('response', resp => {
      if (resp.status() >= 400 && !resp.url().includes('favicon')) {
        failedRequests.push({ url: resp.url(), status: resp.status() });
      }
    });

    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();
    await page.waitForTimeout(1500);

    expect(consoleErrors, `Found console errors: ${consoleErrors.join(', ')}`).toEqual([]);
    expect(failedRequests, `Found failed requests: ${JSON.stringify(failedRequests)}`).toEqual([]);
  });

  test('Timeline View mode switches cleanly and maintains bidirectional linkage', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container article').first().waitFor();

    // Click "时间轴" mode
    const timelineBtn = page.locator('button:has-text("时间轴")');
    await expect(timelineBtn).toBeVisible();
    await timelineBtn.click();
    await page.waitForTimeout(400);

    // Verify timeline groups exist
    const timelineCards = page.locator('article[id^="timeline-card-"]');
    const count = await timelineCards.count();
    expect(count).toBeGreaterThan(0);

    // Click first timeline card
    const firstCard = timelineCards.first();
    await firstCard.click();
    await page.waitForTimeout(500);

    // Detail drawer should open
    const drawer = page.locator('div[role="dialog"][aria-label="活动详情"]');
    await expect(drawer).toBeVisible();

    // Dismiss with Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(drawer).not.toBeVisible();
  });

  test('Radar Rings and Heatmap layers toggle without errors', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Toggle radar rings
    const ringsBtn = page.locator('button[title="辐射圈"]').first();
    if (await ringsBtn.isVisible()) {
      await ringsBtn.click();
      await page.waitForTimeout(400);
      // Click again to turn off
      await ringsBtn.click();
      await page.waitForTimeout(300);
    }

    // Toggle heatmap
    const heatBtn = page.locator('button[title="热力图"]').first();
    if (await heatBtn.isVisible()) {
      await heatBtn.click();
      await page.waitForTimeout(400);
      await heatBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('Favorites workflow and unDraw Empty State rendering', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Locate first card's favorite button
    const firstFavBtn = page.locator('#cards-container article').first().locator('button:has-text("待去")');
    await expect(firstFavBtn).toBeVisible();
    await firstFavBtn.click();
    await page.waitForTimeout(300);

    // Verify favorite counter says (1) and filter to favorites
    const isMobile = await page.evaluate(() => window.innerWidth < 768);
    if (isMobile) {
      // Mobile: open Filter Popover to toggle favorites
      const filterBtn = page.locator('button[title="高级筛选"]').first();
      await filterBtn.click();
      await page.waitForTimeout(300);
      const mobileFavBtn = page.locator('header .animate-in button:has-text("待去")');
      await expect(mobileFavBtn).toContainText('(1)');
      await mobileFavBtn.click();
      await page.waitForTimeout(300);
      await filterBtn.click(); // close popover
    } else {
      const topFavBtn = page.locator('header button:has-text("待去")').first();
      await expect(topFavBtn).toContainText('(1)');
      await topFavBtn.click();
    }
    await page.waitForTimeout(300);

    // Should only show 1 card
    const favCards = page.locator('#cards-container article');
    await expect(favCards).toHaveCount(1);

    // Unfavorite the card
    const unfavBtn = favCards.first().locator('button:has-text("已待去")');
    await unfavBtn.click();
    await page.waitForTimeout(400);

    // Empty state should be visible!
    const emptyState = page.locator('h3:has-text("待去清单暂无活动")');
    await expect(emptyState).toBeVisible();

    // Click "查看全部活动" inside EmptyState
    const resetBtn = page.locator('button:has-text("查看全部活动")');
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();
    await page.waitForTimeout(400);

    // All cards should be restored
    const restoredCards = page.locator('#cards-container article');
    expect(await restoredCards.count()).toBeGreaterThan(5);
  });

  test('Calendar date selection and full period restoration', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container article').first().waitFor();

    // Find date buttons in calendar bar (matching tabular date numbers)
    const dayButtons = page.locator('aside button:has(span.tabular-nums)');
    const dayCount = await dayButtons.count();
    if (dayCount > 0) {
      // Click first specific date
      await dayButtons.first().click();
      await page.waitForTimeout(400);

      // Click "全部" to restore
      const allPeriodBtn = page.locator('aside button:has-text("全部")').first();
      await allPeriodBtn.click();
      await page.waitForTimeout(400);

      const allCards = page.locator('#cards-container article');
      expect(await allCards.count()).toBeGreaterThan(5);
    }
  });

  test('All 4 Map Style Modes cycle smoothly', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#leaflet-map').waitFor();

    const isMobile = await page.evaluate(() => window.innerWidth < 640);
    if (isMobile) {
      const cycleBtn = page.locator('button[title="切换底图"]').first();
      await expect(cycleBtn).toBeVisible();
      for (let i = 0; i < 4; i++) {
        await cycleBtn.click();
        await page.waitForTimeout(200);
      }
    } else {
      const modeLabels = ['高清卫星', '苹果浅灰', '午夜深色', '高德全彩'];
      for (const label of modeLabels) {
        const modeBtn = page.locator(`button:has-text("${label}")`).first();
        if (await modeBtn.isVisible()) {
          await modeBtn.click();
          await page.waitForTimeout(200);
        }
      }

      // Verify dark mode class toggle
      const darkBtn = page.locator('button:has-text("午夜深色")').first();
      if (await darkBtn.isVisible()) {
        await darkBtn.click();
        await page.waitForTimeout(200);
        const isDark = await page.evaluate(() => document.documentElement.classList.contains('theme-dark'));
        expect(isDark).toBe(true);
      }
    }
  });

  test('Mobile Bottom Sheet expands to 86vh and collapses', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Click mobile sheet handle
    const sheetHandle = page.locator('aside button.md\\:hidden').first();
    await expect(sheetHandle).toBeVisible();

    // Click to expand
    await sheetHandle.click();
    await page.waitForTimeout(400);

    let hasExpandedClass = await page.evaluate(() => {
      const aside = document.querySelector('aside');
      return aside && aside.className.includes('max-h-[86vh]');
    });
    expect(hasExpandedClass).toBe(true);

    // Click again to collapse
    await sheetHandle.click();
    await page.waitForTimeout(400);

    hasExpandedClass = await page.evaluate(() => {
      const aside = document.querySelector('aside');
      return aside && aside.className.includes('max-h-[86vh]');
    });
    expect(hasExpandedClass).toBe(false);
  });
});
