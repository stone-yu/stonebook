
import { test, expect } from '@playwright/test';

const mockApi = process.env.MOCK_API_URL || 'http://127.0.0.1:8080';

test.describe('Navigation Sidebar', () => {
    test.beforeEach(async ({ request }) => {
    // Ensure installed
        await request.post(`${mockApi}/_test/reset`, {
            data: { installed: true }
        });
    });

    test('Check all sidebar links', async ({ page }) => {
        await page.goto('/');

        // 1. Home
        await expect(page.locator('nav').getByRole('link', { name: '首页' })).toBeVisible();
        await expect(page.locator('nav').getByRole('link', { name: '首页' })).toHaveAttribute('href', '/');

        // 2. Primary reader tasks
        const links = [
            { name: '我的书架', href: '/user/shelf' },
            { name: '找书', href: '/discover' },
        ];

        for (const link of links) {
            await expect(page.locator('nav').getByRole('link', { name: link.name })).toBeVisible();
            await expect(page.locator('nav').getByRole('link', { name: link.name })).toHaveAttribute('href', link.href);
        }
        await expect(page.locator('nav').getByText('更多', { exact: true })).toBeVisible();
        await expect(page.locator('nav a[href="/library"]')).toHaveCount(0);
        await expect(page.locator('nav a[href="/tag"]')).not.toBeVisible();

    });

    test('Network library entry can be hidden without blocking the route', async ({ page, request }) => {
        await request.post(`${mockApi}/_test/reset`, {
            data: { installed: true, showNetworkLibrary: false }
        });

        await page.goto('/');
        await expect(page.locator('nav').getByRole('link', { name: '网络书库' })).toHaveCount(0);

        await page.goto('/network');
        await expect(page.getByRole('heading', { name: '网络书库' })).toBeVisible();
    });

    test('Sidebar stays visible at md width', async ({ page }) => {
        // md 断点（960~1279）下侧栏也应常驻展示，而非被折叠成抽屉
        await page.setViewportSize({ width: 1100, height: 800 });
        await page.goto('/');

        const homeLink = page.locator('nav').getByRole('link', { name: '首页' });
        await homeLink.waitFor({ state: 'visible' });

        // 抽屉常驻时 nav 位于左侧可视区域（x >= 0）；若被折叠为 temporary 抽屉则会被移出屏幕（x < 0）
        const box = await homeLink.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.x).toBeGreaterThanOrEqual(0);
    });

    test('Can navigate via all sidebar links', async ({ page }) => {
    // Define all links to test
        const linksToTest = [
            { name: '我的书架', url: '/user/shelf', expectedText: '我的书架' },
            { name: '找书', url: '/discover', expectedText: '今天想读什么' },
        ];

        for (const link of linksToTest) {
            await page.goto('/');
            console.log(`Testing navigation to ${link.name}...`);
        
            const navLink = page.locator('nav').getByRole('link', { name: link.name });
            await navLink.waitFor({ state: 'visible' });
            await navLink.click();
        
            await expect(page).toHaveURL(link.url);
            // Verify page content to ensure successful load
            // Note: Some pages might share components (like BookList), so title check is good
            // Adjust selector if needed, e.g. h1, h2, or breadcrumb
            await expect(page.getByText(link.expectedText).first()).toBeVisible();
        }
    });
});
