import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const OUTPUT_DIR = path.resolve(__dirname, '..', 'docs', 'reports', 'ui-after', 'verification');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function run() {
  console.log("Launching Brave Browser...");
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  try {
    console.log("Navigating to recruiter login page at http://localhost:5002/recruiter/login...");
    await page.goto('http://localhost:5002/recruiter/login', { waitUntil: 'networkidle2' });

    console.log("Taking screenshot of login page...");
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_login_page.png') });

    console.log("Filling in seeded credentials...");
    await page.waitForSelector('#email');
    await page.type('#email', 'recruiter.demo@smartonboard.com');
    await page.type('#password', 'Recruiter123!');

    console.log("Submitting login form...");
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
    ]);

    const currentUrl = page.url();
    console.log(`Current page URL after login: ${currentUrl}`);

    if (currentUrl.includes('/recruiter/dashboard')) {
      console.log("✅ SUCCESS: Successfully logged in and loaded recruiter dashboard!");
      await new Promise(r => setTimeout(r, 3000)); // Wait for charts/animations to settle
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_dashboard_success.png') });
      console.log(`Saved dashboard screenshot to: ${path.join(OUTPUT_DIR, 'recruiter_dashboard_success.png')}`);
    } else {
      console.log("❌ FAILURE: Redirection to dashboard failed.");
      const pageText = await page.evaluate(() => document.body.innerText);
      console.log("Page error body text:", pageText.slice(0, 500));
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_login_failure.png') });
      process.exit(1);
    }
  } catch (err) {
    console.error("❌ ERROR: Unexpected error during execution:", err);
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'recruiter_error_state.png') });
    process.exit(1);
  } finally {
    await page.close();
    await browser.close();
  }
}

run().catch(console.error);
