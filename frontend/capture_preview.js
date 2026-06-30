import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const OUTPUT_DIR = path.resolve(__dirname, '..', 'docs', 'reports', 'ui-after', 'design-system-preview');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function run() {
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
    });
    console.log('Browser launched successfully');
  } catch (e) {
    console.error('Failed to launch browser:', e.message);
    process.exit(1);
  }

  const page = await browser.newPage();
  const url = 'http://localhost:5002/design-system-preview';

  const viewports = [
    { name: 'desktop', width: 1440, height: 950 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'mobile', width: 375, height: 812 }
  ];

  try {
    for (const vp of viewports) {
      console.log(`Setting viewport to ${vp.name} (${vp.width}x${vp.height})...`);
      await page.setViewport({ width: vp.width, height: vp.height });
      await page.goto(url, { waitUntil: 'networkidle2' });
      await new Promise(r => setTimeout(r, 2000)); // wait for animations to settle
      
      const screenshotPath = path.join(OUTPUT_DIR, `preview_${vp.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`Saved screenshot to ${screenshotPath}`);
    }
    console.log('All responsive screenshots captured successfully!');
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    await page.close();
    await browser.close();
  }
}

run().catch(console.error);
