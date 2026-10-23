import { test, expect } from '@playwright/test';

test.describe('Spatial Exploration & Apple HIG Interaction Suite', () => {
  test('Search input debouncing and results filtering', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container article').first().waitFor();

    const searchInput = page.locator('input[placeholder*="搜索"]');
    await searchInput.fill('动漫');
    
    // Wait for 200ms debounce
    await page.waitForTimeout(400);

    const cards = page.locator('#cards-container article');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);

    // Click clear button
    const clearBtn = page.locator('header button[aria-label="清空搜索"]');
    if (await clearBtn.isVisible()) {
      await clearBtn.click();
      await page.waitForTimeout(400);
      const resetCount = await cards.count();
      expect(resetCount).toBeGreaterThan(count);
    }
  });

  test('URL deep linking automatically opens target event', async ({ page }) => {
    await page.goto('/index.html?id=seed_all_01');
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();
    await page.waitForTimeout(1000);

    const drawer = page.locator('div[role="dialog"][aria-label="活动详情"]');
    await expect(drawer).toBeVisible();

    // Verify Escape key dismisses
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    await expect(drawer).not.toBeVisible();
  });

  test('Dark mode toggle applies theme-dark frosted glass and native tiles', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    await page.locator('#cards-container').waitFor();

    const darkBtn = page.locator('button:has-text("午夜深色")').first();
    if (await darkBtn.isVisible()) {
      await darkBtn.click();
      await page.waitForTimeout(600);

      const isThemeDark = await page.evaluate(() => {
        return document.querySelector('#app > div').classList.contains('theme-dark');
      });
      expect(isThemeDark).toBe(true);
    }
  });

  test('Keyboard navigation: Enter key opens detail drawer from card', async ({ page }) => {
    await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    const firstCard = page.locator('#cards-container article').first();
    await firstCard.waitFor();

    await firstCard.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(600);

    const drawer = page.locator('div[role="dialog"][aria-label="活动详情"]');
    await expect(drawer).toBeVisible();
  });
});
