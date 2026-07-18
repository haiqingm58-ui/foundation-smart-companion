import { expect, test } from "@playwright/test";


const APP_PATH = "/foundation-smart-companion";
const COPYRIGHT = "All Rights Reserved @2026";


async function readLayout(page) {
  return page.evaluate(() => {
    const rectOf = (selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return {
        top: rect.top,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
      };
    };

    const card = rectOf(".authColumns");
    const footer = rectOf(".authCopyright");
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      page: {
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
      },
      logo: rectOf(".collegeLogo"),
      card,
      footer,
      overlap: card && footer ? Math.max(0, card.bottom - footer.top) : null,
      footerText: document.querySelector(".authCopyright")?.textContent,
    };
  });
}


test("登录页桌面与移动布局保持 Logo 间距和版权流式定位", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1024 });
  await page.goto(`${APP_PATH}/login`);
  await expect(page.getByText(COPYRIGHT, { exact: true })).toBeVisible();
  await expect(page.getByRole("img", { name: "图片验证码" })).toBeVisible();

  const desktop = await readLayout(page);
  expect(desktop.footerText).toBe(COPYRIGHT);
  expect(desktop.logo).not.toBeNull();
  expect(desktop.logo.top).toBeCloseTo(36, 0);
  expect(desktop.logo.width).toBeCloseTo(120, 0);
  expect(desktop.logo.height).toBeCloseTo(120, 0);
  expect(desktop.overlap).toBe(0);
  expect(desktop.footer.bottom).toBeCloseTo(desktop.viewport.height - 24, 0);
  expect(desktop.page.scrollWidth).toBeLessThanOrEqual(desktop.page.clientWidth + 1);

  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = await readLayout(page);
  expect(mobile.footerText).toBe(COPYRIGHT);
  expect(mobile.logo).not.toBeNull();
  expect(mobile.logo.top).toBeCloseTo(20, 0);
  expect(mobile.logo.width).toBeCloseTo(78, 0);
  expect(mobile.logo.height).toBeCloseTo(78, 0);
  expect(mobile.overlap).toBe(0);
  expect(mobile.footer.top).toBeGreaterThanOrEqual(mobile.card.bottom);
  expect(mobile.page.scrollHeight).toBeGreaterThan(mobile.viewport.height);
  expect(mobile.page.scrollWidth).toBeLessThanOrEqual(mobile.page.clientWidth + 1);
});
