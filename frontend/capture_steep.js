import puppeteer from 'puppeteer-core';
import http from 'http';
import fs from 'fs';
import path from 'path';

async function getBrowserWs() {
  return new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json/version', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json.webSocketDebuggerUrl);
        } catch (e) {
          reject(new Error(`Failed to parse debugging JSON: ${e.message}`));
        }
      });
    }).on('error', (e) => {
      reject(new Error(`Failed to contact debugging port: ${e.message}`));
    });
  });
}

async function run() {
  const outputDir = path.resolve('/Users/krishnagarg/smartonboard-main/docs/reports/steep-captures');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  let wsUrl;
  try {
    wsUrl = await getBrowserWs();
    console.log(`Connected to WS: ${wsUrl}`);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }

  const browser = await puppeteer.connect({
    browserWSEndpoint: wsUrl,
    defaultViewport: { width: 1280, height: 800 }
  });

  const page = await browser.newPage();
  
  console.log('Navigating to https://steep.app...');
  await page.goto('https://steep.app', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000)); // Let any entry animations finish

  // Capture hero/landing page top
  console.log('Capturing Steep Hero...');
  await page.screenshot({ path: path.join(outputDir, 'steep_hero.png') });

  // Let's scroll to features
  console.log('Scrolling to feature section...');
  await page.evaluate(() => {
    window.scrollTo(0, 1000);
  });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, 'steep_features.png') });

  // Let's scroll to product showcase
  console.log('Scrolling to product showcase section...');
  await page.evaluate(() => {
    window.scrollTo(0, 2200);
  });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, 'steep_showcase.png') });

  // Let's scroll to dashboard example
  console.log('Scrolling to dashboard section...');
  await page.evaluate(() => {
    window.scrollTo(0, 3600);
  });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, 'steep_dashboard.png') });

  // Let's scroll to pricing / footer / navigation area
  console.log('Scrolling to footer section...');
  await page.evaluate(() => {
    window.scrollTo(0, 4800);
  });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(outputDir, 'steep_footer.png') });

  console.log('Steep screenshot capture completed!');
  await page.close();
  await browser.disconnect();
}

run().catch(console.error);
