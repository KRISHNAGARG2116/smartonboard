import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function run() {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    defaultViewport: { width: 1440, height: 950 }
  });

  const page = await browser.newPage();
  const url = 'https://uxpilot.ai/s/b8cf525a7b1399bfac1296112e464e57';
  console.log(`Navigating to ${url}...`);

  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  console.log('Page loaded. Waiting 10 seconds for React app to fully render...');
  await new Promise(r => setTimeout(r, 10000));

  // Capture screenshot of the first view
  const screenshotPath = path.join(__dirname, 'uxpilot_home.png');
  await page.screenshot({ path: screenshotPath });
  console.log(`Saved screenshot to ${screenshotPath}`);

  // Scrape page DOM content
  const data = await page.evaluate(() => {
    // Let's get the inner text of the body to see what we have
    const bodyText = document.body.innerText;
    
    // Find headings, labels, button texts, or specific elements
    const elements = Array.from(document.querySelectorAll('*')).map(el => {
      const text = el.innerText ? el.innerText.trim() : '';
      const className = el.className || '';
      const id = el.id || '';
      return {
        tag: el.tagName,
        id,
        className,
        text: text.substring(0, 100),
        childrenCount: el.children.length
      };
    });

    // Find images
    const images = Array.from(document.querySelectorAll('img')).map(img => ({
      src: img.src,
      alt: img.alt,
      width: img.width,
      height: img.height
    }));

    // Find links
    const links = Array.from(document.querySelectorAll('a')).map(a => ({
      href: a.href,
      text: a.innerText.trim()
    }));

    return {
      bodyTextLength: bodyText.length,
      bodyTextSnippet: bodyText.substring(0, 4000),
      images,
      links,
      classes: Array.from(new Set(elements.flatMap(e => typeof e.className === 'string' ? e.className.split(' ') : []).filter(Boolean))).slice(0, 100)
    };
  });

  console.log('\n--- BODY TEXT SNIPPET ---');
  console.log(data.bodyTextSnippet);

  console.log('\n--- IMAGES ---');
  console.log(data.images);

  console.log('\n--- LINKS ---');
  console.log(data.links);

  fs.writeFileSync(path.join(__dirname, 'uxpilot_scraped.json'), JSON.stringify(data, null, 2));
  console.log('Saved scraped data to uxpilot_scraped.json');

  await browser.close();
}

run().catch(console.error);
