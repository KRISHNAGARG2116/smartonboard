import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = path.resolve(__dirname, '..', 'scratch');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function autoScroll(page) {
    await page.evaluate(async () => {
        await new Promise((resolve) => {
            let totalHeight = 0;
            const distance = 100;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeight - window.innerHeight) {
                    clearInterval(timer);
                    resolve();
                }
            }, 100);
        });
    });
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
  const url = 'https://steep.app/';

  try {
    console.log(`Navigating to ${url}...`);
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto(url, { waitUntil: 'networkidle2' });
    
    console.log('Scrolling down the page to trigger animations and lazy loading...');
    await autoScroll(page);
    
    // Scroll back to top before screenshot
    await page.evaluate(() => window.scrollTo(0, 0));
    await new Promise(r => setTimeout(r, 1000));
    
    const screenshotPath = path.join(OUTPUT_DIR, `steep_desktop.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Saved screenshot to ${screenshotPath}`);
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    await page.close();
    await browser.close();
  }
}

run().catch(console.error);
