import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const images = [
  {
    name: 'uxpilot_landing.png',
    url: 'https://storage.googleapis.com/uxpilot-auth.appspot.com/screenshots/8692b827cf-73b07d3a25a174e5ae87.png'
  },
  {
    name: 'uxpilot_recruiter_dashboard.png',
    url: 'https://storage.googleapis.com/uxpilot-auth.appspot.com/screenshots/b9ecefd096-c680d843b3546c9ce656.png'
  },
  {
    name: 'uxpilot_candidate_portal.png',
    url: 'https://storage.googleapis.com/uxpilot-auth.appspot.com/screenshots/d4639e286e-47b1b2b1d6480f369531.png'
  }
];

const outputDir = path.join(__dirname, '..', 'docs', 'reports', 'uxpilot-screens');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

function downloadImage(img) {
  return new Promise((resolve, reject) => {
    const dest = path.join(outputDir, img.name);
    const file = fs.createWriteStream(dest);
    https.get(img.url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log(`Downloaded ${img.name} to ${dest}`);
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      console.error(`Failed to download ${img.name}:`, err.message);
      reject(err);
    });
  });
}

async function run() {
  for (const img of images) {
    await downloadImage(img);
  }
  console.log('All downloads completed!');
}

run().catch(console.error);
