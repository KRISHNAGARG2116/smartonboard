import puppeteer from 'puppeteer-core';
import http from 'http';
import fs from 'fs';
import path from 'path';

const APP_PORT = 5002;
const BASE_URL = `http://localhost:${APP_PORT}`;

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
          reject(new Error(`Failed to parse debugging JSON: ${e.message}. Data: ${data}`));
        }
      });
    }).on('error', (e) => {
      reject(new Error(`Failed to contact debugging port: ${e.message}`));
    });
  });
}

async function run() {
  const mode = process.argv[2] || 'before';
  const outputDir = path.resolve(`/Users/krishnagarg/smartonboard-main/docs/reports/ui-${mode}`);
  console.log(`Starting UI Audit in mode: ${mode}`);
  console.log(`Output directory: ${outputDir}`);

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

  // Helper to capture a screenshot after waiting for animations/content
  async function capture(urlPath, filename) {
    const url = `${BASE_URL}${urlPath}`;
    console.log(`Navigating to ${url}...`);
    try {
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 15000 });
      // Sleep a bit for framer motion or other animations to settle
      await new Promise(r => setTimeout(r, 1000));
      const filepath = path.join(outputDir, filename);
      await page.screenshot({ path: filepath, fullPage: false });
      console.log(`Saved screenshot: ${filepath}`);
    } catch (e) {
      console.error(`Failed to capture ${urlPath}: ${e.message}`);
    }
  }

  // Helper to log out
  async function logout() {
    console.log('Logging out (clearing localStorage and cookies)...');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    const client = await page.target().createCDPSession();
    await client.send('Network.clearBrowserCookies');
    await new Promise(r => setTimeout(r, 500));
  }

  // --- 1. PUBLIC ROUTES ---
  await logout();
  await capture('/', 'public_landing.png');
  await capture('/login', 'public_login_selection.png');
  await capture('/recruiter/login', 'public_recruiter_login.png');
  await capture('/recruiter/register', 'public_recruiter_register.png');
  await capture('/candidate/login', 'public_candidate_login.png');
  await capture('/candidate/register', 'public_candidate_register.png');

  // --- 2. CANDIDATE PORTAL ---
  console.log('Logging in as Candidate...');
  await page.goto(`${BASE_URL}/candidate/login`, { waitUntil: 'networkidle2' });
  await page.type('input[type="email"]', 'chrisgergoriginal@gmail.com');
  await page.type('input[type="password"]', 'Password123!');
  await Promise.all([
    page.click('button[type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {})
  ]);
  await new Promise(r => setTimeout(r, 1500));

  const candidateRoutes = [
    { path: '/candidate/dashboard', file: 'candidate_dashboard.png' },
    { path: '/candidate/resumes', file: 'candidate_resumes.png' },
    { path: '/candidate/jobs', file: 'candidate_jobs.png' },
    { path: '/candidate/applications', file: 'candidate_applications.png' },
    { path: '/candidate/interviews', file: 'candidate_interviews.png' },
    { path: '/candidate/profile', file: 'candidate_profile.png' },
    { path: '/candidate/settings', file: 'candidate_settings.png' }
  ];

  for (const route of candidateRoutes) {
    await capture(route.path, route.file);
  }

  // --- 3. RECRUITER PORTAL ---
  await logout();
  console.log('Logging in as Recruiter...');
  await page.goto(`${BASE_URL}/recruiter/login`, { waitUntil: 'networkidle2' });
  await page.type('input[type="email"]', 'e23cseu2390@bennett.com');
  await page.type('input[type="password"]', 'Password123!');
  await Promise.all([
    page.click('button[type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {})
  ]);
  await new Promise(r => setTimeout(r, 1500));

  const recruiterRoutes = [
    { path: '/recruiter/dashboard', file: 'recruiter_dashboard.png' },
    { path: '/recruiter/jobs', file: 'recruiter_jobs.png' },
    { path: '/recruiter/candidates', file: 'recruiter_candidates.png' },
    { path: '/recruiter/pipeline', file: 'recruiter_pipeline.png' },
    { path: '/recruiter/interviews', file: 'recruiter_interviews.png' },
    { path: '/recruiter/analytics', file: 'recruiter_analytics.png' },
    { path: '/recruiter/settings', file: 'recruiter_settings.png' }
  ];

  for (const route of recruiterRoutes) {
    await capture(route.path, route.file);
  }

  console.log('UI Audit screenshotting run complete!');
  await page.close();
  await browser.disconnect();
}

run().catch(console.error);
