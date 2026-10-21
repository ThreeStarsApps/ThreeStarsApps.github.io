// Optional browser checks: npm install, then npm run check:browser.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { parseArgs } = require('node:util');

const options = parseArgs({ options: {
  url: { type: 'string', default: 'http://127.0.0.1:4173' },
  root: { type: 'string', default: path.resolve(__dirname, '..') },
  browser: { type: 'string', default: 'msedge' },
  screenshots: { type: 'string', default: path.resolve(__dirname, '../.qa/browser') },
} }).values;
const root = path.resolve(options.root);
const base = options.url.replace(/\/$/, '');

(async () => {
  const browser = await chromium.launch({ channel: options.browser, headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    const goto = async (url) => {
      const response = await page.goto(base + url);
      assert.equal(response.status(), 200, url);
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(async () => {
        const images = [...document.images].filter(image => image.getAttribute('src'));
        images.forEach(image => { image.loading = 'eager'; });
        await Promise.all(images.map(image => image.decode()));
      });
    };
    const checkOverflow = async (label) => {
      const sizes = await page.evaluate(() => ({ screen: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
      assert.ok(sizes.content <= sizes.screen + 1, `${label}: horizontal overflow (${JSON.stringify(sizes)})`);
    };
    const qa = path.resolve(options.screenshots);
    await fs.mkdir(qa, { recursive: true });
    await goto('/');
    await checkOverflow('Desktop homepage');
    await page.screenshot({ path: path.join(qa, 'home-desktop.png') });
    await page.screenshot({ path: path.join(qa, 'home-full.png'), fullPage: true });
    const demo = page.locator('[data-shortcut-demo]');
    assert.equal(await demo.locator('[data-demo-action]').textContent(), 'Play / Pause');
    await demo.getByRole('button', { name: 'Double', exact: true }).click();
    assert.equal(await demo.locator('[data-demo-label]').textContent(), 'Volume Down · Double Press');
    assert.equal(await demo.locator('[data-demo-action]').textContent(), 'Sound Mode');
    await demo.getByRole('button', { name: 'Long', exact: true }).click();
    assert.equal(await demo.locator('[data-demo-label]').textContent(), 'Power · Long Press');
    assert.equal(await demo.locator('[data-demo-action]').textContent(), 'Torch');
    await demo.getByRole('button', { name: 'PenStar', exact: true }).click();
    assert.deepEqual(await demo.locator('[data-demo-trigger]').allTextContents(), ['Single', 'Up', 'Down']);
    assert.equal(await demo.getByRole('button', { name: 'Down', exact: true }).getAttribute('aria-pressed'), 'true');
    assert.equal(await demo.locator('[data-demo-action]').textContent(), 'Previous Reel');
    await demo.getByRole('button', { name: 'Up', exact: true }).click();
    assert.equal(await demo.locator('[data-demo-action]').textContent(), 'Next Reel');
    await demo.getByRole('button', { name: 'Single', exact: true }).click();
    assert.equal(await demo.locator('[data-demo-action]').textContent(), 'Play / Pause');
    assert.equal(await demo.locator('[data-demo-description]').textContent(), 'Play or pause the current reel in Instagram.');
    await demo.getByRole('button', { name: 'KeyStar', exact: true }).click();
    assert.deepEqual(await demo.locator('[data-demo-trigger]').allTextContents(), ['Single', 'Double', 'Long']);
    assert.equal(await demo.locator('[data-demo-label]').textContent(), 'Volume Up · Single Press');

    await goto('/guides/');
    const guides = JSON.parse(await fs.readFile(path.join(__dirname, '../src/content/guides.json'), 'utf8'));
    assert.equal(await page.locator('.guide-card:visible').count(), guides.length);
    await page.screenshot({ path: path.join(qa, 'guides-desktop.png'), fullPage: true });

    await goto('/keystar/support/#collapseShizukuSetup');
    assert.ok(await page.locator('#collapseShizukuSetup').evaluate(element => element.open));
    const search = page.getByRole('searchbox', { name: 'Find an answer' });
    await search.fill('nothing-matches-this-phrase');
    assert.equal(await page.locator('.faq-item:visible').count(), 0);
    await page.getByText('No answers found.', { exact: false }).waitFor();
    await search.fill('volume');
    assert.ok(await page.locator('.faq-item:visible').count() > 0);
    await page.locator('.support-aside').getByRole('link', { name: 'Compatible devices' }).click();
    assert.equal(await search.inputValue(), '');
    assert.ok(await page.locator('#collapseSupportedDevices').evaluate(element => element.open));
    await page.screenshot({ path: path.join(qa, 'support-desktop.png') });

    await goto('/penstar/');
    await page.getByRole('link', { name: 'Enlarge PenStar screenshot 1' }).click();
    await page.getByRole('dialog', { name: 'App screenshot' }).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('dialog', { name: 'App screenshot' }).isVisible(), false);
    assert.ok(await page.getByRole('link', { name: 'Enlarge PenStar screenshot 1' }).evaluate(element => element === document.activeElement));
    await page.evaluate(() => { document.activeElement.blur(); window.scrollTo(0, 0); });
    await page.mouse.move(0, 0);
    await page.screenshot({ path: path.join(qa, 'product-desktop.png'), fullPage: true });

    const sitemap = await fs.readFile(path.join(root, 'sitemap.xml'), 'utf8');
    const routes = [...sitemap.matchAll(/<loc>https:\/\/threestarsapps\.com([^<]+)<\/loc>/g)].map(match => match[1]);
    for (const width of [1440, 800, 390, 320]) {
      await page.setViewportSize({ width, height: width === 1440 ? 1000 : 844 });
      for (const route of routes) {
        await goto(route);
        await checkOverflow(`${width}px ${route}`);
        assert.equal(await page.locator('h1').count(), 1);
        const filename = route === '/' ? 'home' : route.replace(/^\/|\/$/g, '').replaceAll('/', '_');
        await page.screenshot({ path: path.join(qa, `${width}-${filename}.png`), fullPage: true });
        if (/^\/(keystar|penstar)\/support\/$/.test(route)) {
          const contact = page.locator('.support-contact .btn');
          const textLines = await contact.evaluate(element => {
            const range = document.createRange();
            range.selectNodeContents(element);
            return range.getClientRects().length;
          });
          assert.equal(textLines, 1, `${width}px ${route}: contact button text wraps`);
        }
      }
    }
    const missing = await page.request.get(base + '/this-page-does-not-exist/');
    assert.equal(missing.status(), 404);
    assert.match(await missing.text(), /<h1>404<\/h1>/);
    await page.setViewportSize({ width: 390, height: 844 });
    await goto('/');
    await page.screenshot({ path: path.join(qa, 'home-mobile.png'), fullPage: true });
    const menu = page.getByRole('button', { name: 'Menu' });
    await menu.click();
    assert.equal(await menu.getAttribute('aria-expanded'), 'true');
    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'KeyStar', exact: true }).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await menu.getAttribute('aria-expanded'), 'false');
    await goto('/guides/');
    await page.screenshot({ path: path.join(qa, 'guides-mobile.png'), fullPage: true });
    await goto('/guides/map-s-pen-button-air-actions/');
    await page.screenshot({ path: path.join(qa, 'guide-mobile.png'), fullPage: true });
    await goto('/keystar/support');
    await page.getByRole('heading', { name: 'KeyStar Support', exact: true }).waitFor();
    await page.locator('.support-contact').getByRole('link', { name: 'Contact the developer', exact: true }).click();
    assert.equal(new URL(page.url()).pathname, '/contact/');

    for (const app of ['keystar', 'penstar']) {
      await goto(`/${app}/support`);
      assert.equal(new URL(page.url()).pathname, `/${app}/support/`);
      await goto(`/${app}/privacy_policy`);
      assert.equal(new URL(page.url()).pathname, `/${app}/privacy_policy/`);
      await goto(`/${app}/support/#collapseShizukuSetup`);
      await page.locator('#collapseShizukuSetup[open]').waitFor();
      for (const slug of ['support', 'privacy_policy']) {
        await assert.rejects(fs.access(path.join(root, app, `${slug}.html`)), { code: 'ENOENT' });
        const removed = await page.request.get(`${base}/${app}/${slug}.html`);
        assert.equal(removed.status(), 404, `Old URL should be removed: /${app}/${slug}.html`);
      }
    }

    const noJs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const plain = await noJs.newPage();
    await plain.goto(base + '/penstar/support/');
    await plain.locator('#collapseSupportedDevices summary').click();
    assert.ok(await plain.locator('#collapseSupportedDevices').evaluate(element => element.open));
    assert.ok(await plain.getByRole('navigation', { name: 'Main navigation' }).isVisible());
    await noJs.close();
    assert.deepEqual(errors, [], `Browser errors: ${errors.join(', ')}`);
    console.log(`PASS: ${routes.length} pages at 1440px, 800px, 390px, and 320px; shortcut preview, guide cards, FAQ search, clean URLs, removed legacy URLs, FAQ deep links, mobile menu, image dialog, custom 404, and no-JavaScript support.`);
    console.log(`Screenshots saved in ${qa}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
