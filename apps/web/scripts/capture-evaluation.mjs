import {chromium} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root = new URL('../../../', import.meta.url);
const output = new URL('experiments/reports/ollama/', root);
const rows = JSON.parse(await readFile(new URL('evaluation.json', output), 'utf8'));
const row = rows.find(r => r.provider === 'ollama' && r.session?.status === 'completed'
  && !r.session.report?.model_usage?.error && r.session.report?.model_usage?.calls > 0);
if (!row) throw new Error('A completed real Ollama evaluation is required');
const browser = await chromium.launch();
const page = await browser.newPage({viewport:{width:1440,height:1000}});
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto(process.env.PGO_WEB_URL || 'http://localhost:3000');
  if (process.env.PGO_API_TOKEN) await page.getByLabel('API access token').fill(process.env.PGO_API_TOKEN);
  await page.getByRole('button', {name:row.session.id.slice(0,8), exact:true}).click();
  await page.getByRole('status').filter({hasText:`Session ${row.session.id} | completed`}).waitFor();
  await page.getByText('Acceptance policy and model usage', {exact:true}).click();
  await page.getByText('Original execution plan', {exact:true}).click();
  await page.screenshot({path:fileURLToPath(new URL('workspace-desktop.png', output)),fullPage:true,animations:'disabled'});
  await page.setViewportSize({width:390,height:844});
  if (await page.evaluate(() => document.documentElement.scrollWidth) > 390) throw new Error('Mobile layout overflow');
  await page.screenshot({path:fileURLToPath(new URL('workspace-mobile.png', output)),fullPage:true,animations:'disabled'});
  await writeFile(new URL('browser-check.json', output), JSON.stringify({
    session_id:row.session.id, provider:'ollama', model:row.session.report.model_usage.model,
    captured_at:new Date().toISOString(), page_errors:errors,
  }, null, 2));
  if (errors.length) throw new Error(errors.join('\n'));
} finally {
  await browser.close();
}
