import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const OUTPUT_DIR = path.resolve(__dirname, '..', 'docs', 'reports', 'ui-after', 'verification');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Use unique email per run
const TEST_EMAIL = `wizard.test_${Date.now()}@company.com`;

function runDbHelper(arg) {
  try {
    const cmd = `PYTHONPATH=../backend python verify_db_helper.py ${arg}`;
    console.log(`Running: ${cmd}`);
    const output = execSync(cmd, { cwd: __dirname }).toString();
    console.log(output);
  } catch (err) {
    console.error("DB Helper failed:", err.message);
  }
}

async function clickButtonWithText(page, text) {
  const buttons = await page.$$('button');
  for (const button of buttons) {
    const val = await page.evaluate(el => el.innerText, button);
    if (val.includes(text)) {
      await button.click();
      return;
    }
  }
  throw new Error(`Button with text "${text}" not found. Current URL: ${page.url()}`);
}

async function clearAndType(page, selector, text) {
  await page.focus(selector);
  await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (el) {
      el.value = '';
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }, selector);
  if (text) {
    await page.type(selector, text);
  }
}

async function run() {
  console.log(`Starting E2E wizard test for ${TEST_EMAIL}`);
  console.log("Launching Brave Browser...");
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  try {
    // 1. Navigate to register
    console.log("Navigating to recruiter registration...");
    await page.goto('http://localhost:5002/recruiter/register', { waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01_recruiter_register_page.png') });

    // 2. Fill registration details
    console.log("Filling registration details...");
    await page.type('#company', 'Wizard Test Inc');
    await page.type('#fullName', 'Wizard Tester');
    await page.type('#email', TEST_EMAIL);
    await page.type('#password', 'Recruiter123!');
    await page.screenshot({ path: path.join(OUTPUT_DIR, '02_recruiter_register_filled.png') });

    // 3. Submit registration
    console.log("Submitting registration...");
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
    ]);
    console.log(`URL after registration: ${page.url()}`);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '03_recruiter_verify_email_page.png') });

    // 4. Mark email as verified in DB
    console.log("Bypassing verification step by marking email verified in database...");
    runDbHelper(`--verify ${TEST_EMAIL}`);

    // 5. Navigate to login and log in
    console.log("Navigating to login...");
    await page.goto('http://localhost:5002/recruiter/login', { waitUntil: 'networkidle2' });
    await page.type('#email', TEST_EMAIL);
    await page.type('#password', 'Recruiter123!');
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
    ]);
    
    // Wait 2 seconds for client-side routing to settle
    await new Promise(r => setTimeout(r, 2000));
    console.log(`URL after login and settle: ${page.url()}`);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '04_onboarding_wizard_step1.png') });

    // 6. Test Step 1 Validation: Click Next without filling anything
    console.log("Testing Step 1 empty validation...");
    await clickButtonWithText(page, 'Next Step');
    await new Promise(r => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(OUTPUT_DIR, '05_step1_validation_empty.png') });

    // 7. Test Step 1 Validation: Enter invalid website
    console.log("Testing Step 1 invalid website validation...");
    await clearAndType(page, '#company-name', 'Wizard Test Inc');
    await clearAndType(page, '#company-website', 'invalid_site');
    await clickButtonWithText(page, 'Next Step');
    await new Promise(r => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(OUTPUT_DIR, '06_step1_validation_invalid_website.png') });

    // 8. Test Step 1 Validation: Enter correct website, industry, size and submit
    console.log("Submitting Step 1 with correct details...");
    await clearAndType(page, '#company-website', 'https://wizard-test.com');
    await clearAndType(page, '#company-industry', 'HR Technology');
    await page.screenshot({ path: path.join(OUTPUT_DIR, '07_step1_correct_filled.png') });

    // Click next to advance to Step 2
    await clickButtonWithText(page, 'Next Step');
    await page.waitForFunction(() => document.body.innerText.includes('Post Your First Job'), { timeout: 10000 });
    console.log("Advanced to Step 2: Post Job!");
    await page.screenshot({ path: path.join(OUTPUT_DIR, '08_onboarding_wizard_step2.png') });

    // 9. Step 2 (Optional Job Creation): Fill job title and click Next
    console.log("Filling Step 2 job title...");
    await page.type('#job-title', 'E2E Test Automation Specialist');
    await clickButtonWithText(page, 'Next Step');

    // Wait for Step 3
    await page.waitForFunction(() => document.body.innerText.includes('Configure Hiring Pipeline'), { timeout: 10000 });
    console.log("Advanced to Step 3: Hiring Pipeline Configuration!");
    await page.screenshot({ path: path.join(OUTPUT_DIR, '09_onboarding_wizard_step3.png') });

    // 10. Step 3 (Hiring Pipeline): Click Next Step
    await clickButtonWithText(page, 'Next Step');

    // Wait for Step 4
    await page.waitForFunction(() => document.body.innerText.includes('Invite Team Members'), { timeout: 10000 });
    console.log("Advanced to Step 4: Invite Team Members!");
    await page.screenshot({ path: path.join(OUTPUT_DIR, '10_onboarding_wizard_step4.png') });

    // 11. Step 4 (Invite Teammates): Fill teammate email and click Next Step
    await page.type('#team-email', 'co-tester@company.com');
    await clickButtonWithText(page, 'Next Step');

    // Wait for Step 5 (Completed screen)
    await page.waitForFunction(() => document.body.innerText.includes('Workspace Setup Completed!'), { timeout: 10000 });
    console.log("Advanced to Step 5: Completed Summary!");
    await page.screenshot({ path: path.join(OUTPUT_DIR, '11_onboarding_wizard_step5.png') });

    // 12. Step 5: Click Enter Dashboard
    console.log("Entering recruiter dashboard...");
    await Promise.all([
      clickButtonWithText(page, 'Enter Dashboard'),
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 })
    ]);
    console.log(`URL after entering dashboard: ${page.url()}`);
    await new Promise(r => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(OUTPUT_DIR, '12_recruiter_dashboard_onboarding_success.png') });

    console.log("✅ SUCCESS: Successfully completed onboarding wizard and loaded cockpit dashboard!");

  } catch (err) {
    console.error("❌ ERROR: E2E test failed:", err);
    try {
      const pageText = await page.evaluate(() => document.body.innerText);
      console.log("Page body text at failure:", pageText.slice(0, 1000));
    } catch (e) {
      console.error("Could not fetch page body text:", e.message);
    }
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'onboarding_error_state.png') });
  } finally {
    await page.close();
    browser.close();
  }
}

run().catch(console.error);
