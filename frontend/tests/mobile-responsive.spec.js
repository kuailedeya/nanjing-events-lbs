import { test, expect } from '@playwright/test';

test.describe('Mobile Viewport & Touch Responsiveness Suite', () => {
  test.use({ viewport: { width: 390, height: 844 } }); // iPhone 14/15 viewport

  test('Top Floating Island fits within mobile screen without overflow', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    const dimensions = await page.evaluate(() => {
      const h = document.querySelector('header > div');
      return {
        scrollWidth: h.scrollWidth,
        clientWidth: h.clientWidth,
        isOverflowing: h.scrollWidth > h.clientWidth + 5
      };
    });

    expect(dimensions.isOverflowing).toBe(false);
  });

  test('Mobile filter popover can be toggled smoothly', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    const filterBtn = page.locator('button[title="高级筛选"]');
    await filterBtn.click();
    await page.waitForTimeout(400);

    // Popover content should be visible
    const popover = page.locator('header .animate-in');
    await expect(popover).toBeVisible();

    // Toggle free only filter
    const freeOnlyBtn = page.locator('button:has-text("仅看免费")');
    if (await freeOnlyBtn.isVisible()) {
      await freeOnlyBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('Mobile floating action tools stack is accessible', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    // Recentering button in floating controls
    const recenterBtn = page.locator('button[title="复位新街口"]').last();
    await expect(recenterBtn).toBeVisible();
    await recenterBtn.click();
    await page.waitForTimeout(400);

    // Bottom sheet is visible and functional
    const bottomSheet = page.locator('aside');
    await expect(bottomSheet).toBeVisible();
  });
});
