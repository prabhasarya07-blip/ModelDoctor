/**
 * Parity harness: compares the Next.js Route Handlers against the
 * original FastAPI backend for every built-in sample snippet.
 *
 * Usage:  node scripts/parity-check.mjs [tsBase] [pyBase]
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const TS = process.argv[2] || "http://localhost:3111";
const PY = process.argv[3] || "http://127.0.0.1:8123";

const src = readFileSync(join(here, "..", "src", "lib", "sample-codes.ts"), "utf8");

// Extract each `code: \`...\`` template literal along with its title.
const samples = [];
const entryRe = /title:\s*"([^"]+)"[\s\S]*?code:\s*`([\s\S]*?)`/g;
let m;
while ((m = entryRe.exec(src)) !== null) {
  samples.push({ title: m[1], code: m[2] });
}
console.log(`Loaded ${samples.length} sample snippets\n`);

async function post(base, path, body) {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { status: res.status, json: await res.json() };
}

let pass = 0;
let fail = 0;

for (const { title, code } of samples) {
  const [py, ts] = await Promise.all([
    post(PY, "/api/quick-scan", { code, language: "python" }),
    post(TS, "/api/quick-scan", { code, language: "python" }),
  ]);

  const pyIds = (py.json.flags ?? []).map((f) => f.pattern_id).sort().join(",");
  const tsIds = (ts.json.flags ?? []).map((f) => f.pattern_id).sort().join(",");
  const scanOk = pyIds === tsIds;

  const [pyD, tsD] = await Promise.all([
    post(PY, "/api/diagnose", { code, language: "python" }),
    post(TS, "/api/diagnose", { code, language: "python" }),
  ]);

  const pyIssueIds = (pyD.json.issues ?? []).map((i) => i.id).sort().join(",");
  const tsIssueIds = (tsD.json.issues ?? []).map((i) => i.id).sort().join(",");
  const scoreOk = pyD.json.health_score === tsD.json.health_score;
  const diagOk = pyIssueIds === tsIssueIds && scoreOk;

  const ok = scanOk && diagOk;
  ok ? pass++ : fail++;

  console.log(`${ok ? "PASS" : "FAIL"}  ${title}`);
  if (!ok) {
    if (!scanOk) {
      console.log(`      scan  py=[${pyIds}]`);
      console.log(`      scan  ts=[${tsIds}]`);
    }
    if (!diagOk) {
      console.log(`      issue py=[${pyIssueIds}] score=${pyD.json.health_score}`);
      console.log(`      issue ts=[${tsIssueIds}] score=${tsD.json.health_score}`);
    }
  }
}

console.log(`\n${pass} passed, ${fail} failed`);
// Set exitCode rather than calling process.exit(): calling exit() while
// undici's keep-alive sockets are still open trips a libuv assertion on Windows.
process.exitCode = fail ? 1 : 0;
