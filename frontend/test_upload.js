import puppeteer from 'puppeteer-core';
import http from 'http';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://localhost:5002';
const BACKEND_URL = 'http://localhost:8000';

async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function run() {
  const outputDir = path.resolve('/Users/krishnagarg/smartonboard-main/frontend');
  const dummyResumePath = path.join(outputDir, 'dummy_resume.txt');
  fs.writeFileSync(dummyResumePath, 'This is a dummy resume. Skills: Python, FastAPI, React, JavaScript, HTML, CSS.');

  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
      defaultViewport: { width: 1280, height: 800 }
    });
    console.log('Browser launched');
  } catch (e) {
    console.error('Failed to launch browser:', e.message);
    process.exit(1);
  }

  const page = await browser.newPage();

  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  page.on('pageerror', err => console.error('BROWSER PAGE ERROR:', err.message));
  page.on('requestfailed', request => {
    console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText);
  });
  page.on('response', async response => {
    console.log('HTTP RESPONSE:', response.url(), response.status());
    if (response.status() >= 400) {
      try {
        const text = await response.text();
        console.log('HTTP ERROR BODY:', text.substring(0, 500));
      } catch (e) {}
    }
  });

  // Helper to clear cookies and localStorage
  async function logout() {
    console.log('Logging out...');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    const client = await page.target().createCDPSession();
    await client.send('Network.clearBrowserCookies');
    await new Promise(r => setTimeout(r, 500));
  }

  await logout();

  // 1. Register candidate
  console.log('Registering candidate...');
  await page.goto(`${BASE_URL}/candidate/register`, { waitUntil: 'domcontentloaded' });
  
  const uniqueEmail = `upload_test_${Date.now()}@example.com`;
  const uniquePhone = `+1555019${String(Math.floor(1000 + Math.random() * 9000))}`;
  await page.type('#fullName', 'Upload Tester');
  await page.type('#email', uniqueEmail);
  await page.type('#phoneNumber', uniquePhone);
  await page.type('#password', 'Password123!');
  await page.click('button[type="submit"]');
  
  await page.waitForSelector('#emailCode', { timeout: 15000 });
  
  // 2. Retrieve & enter OTPs
  const otps = await fetchJson(`${BACKEND_URL}/api/v1/auth/test/otps?email=${encodeURIComponent(uniqueEmail)}`);
  console.log('OTPs:', otps);
  
  await page.type('#emailCode', otps.email_code);
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 1000));
  
  await page.type('#phoneCode', otps.phone_code);
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const verifyPhoneButton = buttons.find(b => b.textContent.includes('Verify & Activate Profile'));
    if (verifyPhoneButton) verifyPhoneButton.click();
  });
  
  // Wait for redirect to dashboard
  console.log('Waiting for redirect to dashboard...');
  await new Promise(r => setTimeout(r, 6000));
  console.log('Current URL after registration:', page.url());

  // Bypass the onboarding wizard check
  await page.evaluate((email) => {
    localStorage.setItem(`smartonboard_onboarded_candidate_${email}`, 'true');
  }, uniqueEmail);
  console.log('Set onboarding flag in localStorage');

  // 3. Navigate to resumes library
  console.log('Navigating to Resume Library...');
  await page.goto(`${BASE_URL}/candidate/resumes`, { waitUntil: 'domcontentloaded' });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(outputDir, 'resumes_page_loaded.png') });

  // 4. Locate file input and upload file
  console.log('Selecting and uploading file...');
  const fileInput = await page.$('input[type="file"]');
  if (fileInput) {
    await fileInput.uploadFile(dummyResumePath);
    console.log('File uploaded to input');
  } else {
    console.error('File input not found');
  }

  // Wait 10 seconds to see if the request completes or hangs
  console.log('Waiting 10 seconds for upload response...');
  await new Promise(r => setTimeout(r, 10000));
  await page.screenshot({ path: path.join(outputDir, 'after_upload_attempt.png') });

  await page.close();
  await browser.disconnect();
}

run().catch(console.error);
