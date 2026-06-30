const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'next_f_strings.txt');
if (!fs.existsSync(filePath)) {
  console.error("next_f_strings.txt not found");
  process.exit(1);
}

const content = fs.readFileSync(filePath, 'utf8');

// Look for anything resembling a JSON or screen array.
// Let's search for keywords: "Candidate Login", "Dashboard", "Rust", "color", "canvas", etc.
const keywords = [
  "Candidate Login", "Candidate Register", "Candidate Verification",
  "Recruiter Login", "Recruiter Setup Company", "Candidate Dashboard",
  "Recruiter Dashboard", "Pipeline Board", "color", "accent", "#", "font", "serif"
];

console.log("=== KEYWORD OCCURRENCES ===");
keywords.forEach(kw => {
  const count = (content.match(new RegExp(kw, 'gi')) || []).length;
  console.log(`"${kw}": ${count} times`);
});

// Let's print out context lines around some of these keywords
console.log("\n=== SCREEN / DESIGN DATA SAMPLES ===");
const lines = content.split('\n');
lines.forEach((line, index) => {
  if (line.includes("Candidate Login") || line.includes("Recruiter Dashboard") || line.includes("Pipeline Board") || line.includes("Setup Company") || line.includes("setup-company")) {
    console.log(`Line ${index + 1}: ${line.substring(0, 500)}...`);
  }
});
