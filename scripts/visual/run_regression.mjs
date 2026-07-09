/**
 * Playwright ビジュアル回帰テスト
 */
import { chromium } from '@playwright/test';
import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '../..');

async function loadViewports() {
  try {
    const text = readFileSync(join(ROOT, 'config/quality-gates.example.yaml'), 'utf-8');
    if (text.includes('desktop')) {
      return [
        { width: 1280, height: 720, name: 'desktop' },
        { width: 375, height: 812, name: 'mobile' },
      ];
    }
  } catch { /* use default */ }
  return [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 375, height: 812, name: 'mobile' },
  ];
}

async function main() {
  const args = process.argv.slice(2);
  const sessionId = args.find(a => !a.startsWith('--'));
  const update = args.includes('--update');
  const urlIdx = args.indexOf('--url');
  const baseUrl = urlIdx >= 0 ? args[urlIdx + 1] : (process.env.WP_STAGING_URL || '');

  if (!sessionId) {
    console.error('Usage: node run_regression.mjs <session_id> [--update] [--url <url>]');
    process.exit(1);
  }

  const sessionDir = join(ROOT, 'output', sessionId);
  const visualDir = join(sessionDir, 'visual');
  const baselineDir = join(visualDir, 'baseline');
  const currentDir = join(visualDir, 'current');
  const diffDir = join(visualDir, 'diff');
  [baselineDir, currentDir, diffDir].forEach(d => mkdirSync(d, { recursive: true }));

  const viewports = await loadViewports();
  const browser = await chromium.launch();
  const results = [];

  let pagePath = '/';
  const taskPath = join(sessionDir, 'task.json');
  if (existsSync(taskPath)) {
    const task = JSON.parse(readFileSync(taskPath, 'utf-8'));
    const slug = task.manifest?.target?.page_slug;
    if (slug) pagePath = `/${slug}/`;
  }

  for (const vp of viewports) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
    const name = `${vp.name}.png`;
    const currentPath = join(currentDir, name);
    const baselinePath = join(baselineDir, name);

    if (baseUrl) {
      try {
        await page.goto(`${baseUrl.replace(/\/$/, '')}${pagePath}`, { waitUntil: 'networkidle', timeout: 30000 });
      } catch (e) {
        console.warn(`WARN: ${baseUrl} アクセス失敗: ${e.message}`);
      }
    } else {
      const wpDir = join(sessionDir, 'wordpress');
      const renderPhp = join(wpDir, 'render.php');
      const htmlFile = [join(wpDir, 'preview.html'), join(wpDir, 'content.html')]
        .find(f => existsSync(f));
      if (htmlFile) {
        await page.goto(`file://${htmlFile}`);
      } else if (existsSync(renderPhp)) {
        const html = `<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="file://${join(wpDir, 'style.css')}"></head><body>${readFileSync(renderPhp, 'utf-8').replace(/<\?php[\s\S]*?\?>/g, '')}</body></html>`;
        const previewPath = join(wpDir, 'preview.html');
        writeFileSync(previewPath, html);
        await page.goto(`file://${previewPath}`);
      }
    }

    await page.screenshot({ path: currentPath, fullPage: true });
    await page.close();

    if (update || !existsSync(baselinePath)) {
      copyFileSync(currentPath, baselinePath);
      results.push({ viewport: vp.name, passed: true, action: 'baseline_updated' });
      continue;
    }

    const current = readFileSync(currentPath);
    const baseline = readFileSync(baselinePath);
    const passed = current.equals(baseline);
    results.push({ viewport: vp.name, passed, diffBytes: passed ? 0 : Math.abs(current.length - baseline.length) });
    if (!passed) {
      copyFileSync(currentPath, join(diffDir, name));
    }
  }

  await browser.close();

  const passed = results.every(r => r.passed);
  const report = { session_id: sessionId, passed, results, base_url: baseUrl || 'local' };
  writeFileSync(join(sessionDir, 'visual_regression.json'), JSON.stringify(report, null, 2));

  console.log(`VISUAL REGRESSION ${passed ? 'PASSED' : 'FAILED'}: ${sessionId}`);
  for (const r of results) {
    console.log(`  [${r.passed ? 'OK' : 'NG'}] ${r.viewport}`);
  }
  process.exit(passed ? 0 : 1);
}

main().catch(e => { console.error(e); process.exit(1); });
