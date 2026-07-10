/**
 * Playwright ビジュアル回帰テスト（ピクセル差分対応）
 */
import { chromium } from '@playwright/test';
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  copyFileSync,
} from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '../..');

const DEFAULT_MAX_DIFF_RATIO = 0.02;
const DEFAULT_THRESHOLD = 0.1;

function loadThresholds() {
  try {
    const yamlPath = join(ROOT, 'config', 'quality-gates.yaml');
    const example = join(ROOT, 'config', 'quality-gates.example.yaml');
    const path = existsSync(yamlPath) ? yamlPath : example;
    if (!existsSync(path)) {
      return { maxDiffRatio: DEFAULT_MAX_DIFF_RATIO, threshold: DEFAULT_THRESHOLD };
    }
    const text = readFileSync(path, 'utf-8');
    const ratio = text.match(/max_diff_ratio:\s*([0-9.]+)/);
    const thr = text.match(/pixel_threshold:\s*([0-9.]+)/);
    return {
      maxDiffRatio: ratio ? Number(ratio[1]) : DEFAULT_MAX_DIFF_RATIO,
      threshold: thr ? Number(thr[1]) : DEFAULT_THRESHOLD,
    };
  } catch {
    return { maxDiffRatio: DEFAULT_MAX_DIFF_RATIO, threshold: DEFAULT_THRESHOLD };
  }
}

async function loadViewports() {
  return [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 375, height: 812, name: 'mobile' },
  ];
}

function compareImages(baselinePath, currentPath, diffPath, opts) {
  const img1 = PNG.sync.read(readFileSync(baselinePath));
  const img2 = PNG.sync.read(readFileSync(currentPath));
  const width = Math.min(img1.width, img2.width);
  const height = Math.min(img1.height, img2.height);

  if (img1.width !== img2.width || img1.height !== img2.height) {
    // サイズ違い: 差分画像は current をコピーし、失敗扱い
    copyFileSync(currentPath, diffPath);
    return {
      passed: false,
      diffPixels: -1,
      diffPercent: 100,
      reason: `size_mismatch ${img1.width}x${img1.height} vs ${img2.width}x${img2.height}`,
    };
  }

  const diff = new PNG({ width, height });
  const diffPixels = pixelmatch(
    img1.data,
    img2.data,
    diff.data,
    width,
    height,
    { threshold: opts.threshold },
  );
  writeFileSync(diffPath, PNG.sync.write(diff));
  const total = width * height;
  const diffPercent = (diffPixels / total) * 100;
  const passed = diffPixels / total <= opts.maxDiffRatio;
  return {
    passed,
    diffPixels,
    diffPercent: Number(diffPercent.toFixed(4)),
    totalPixels: total,
  };
}

async function settlePage(page) {
  await page.addStyleTag({
    content:
      '*, *::before, *::after { animation: none !important; transition: none !important; } #hero { opacity: 1 !important; }',
  });
  await page.waitForTimeout(200);
}

async function main() {
  const args = process.argv.slice(2);
  const sessionId = args.find((a) => !a.startsWith('--'));
  const update = args.includes('--update');
  const urlIdx = args.indexOf('--url');
  const baseUrl = urlIdx >= 0 ? args[urlIdx + 1] : process.env.WP_STAGING_URL || '';

  if (!sessionId) {
    console.error('Usage: node run_regression.mjs <session_id> [--update] [--url <url>]');
    process.exit(1);
  }

  const opts = loadThresholds();
  const sessionDir = join(ROOT, 'output', sessionId);
  const visualDir = join(sessionDir, 'visual');
  const baselineDir = join(visualDir, 'baseline');
  const currentDir = join(visualDir, 'current');
  const diffDir = join(visualDir, 'diff');
  [baselineDir, currentDir, diffDir].forEach((d) => mkdirSync(d, { recursive: true }));

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
    const page = await browser.newPage({
      viewport: { width: vp.width, height: vp.height },
    });
    const name = `${vp.name}.png`;
    const currentPath = join(currentDir, name);
    const baselinePath = join(baselineDir, name);
    const diffPath = join(diffDir, name);

    if (baseUrl) {
      try {
        await page.goto(`${baseUrl.replace(/\/$/, '')}${pagePath}`, {
          waitUntil: 'networkidle',
          timeout: 30000,
        });
      } catch (e) {
        console.warn(`WARN: ${baseUrl} アクセス失敗: ${e.message}`);
      }
    } else {
      const wpDir = join(sessionDir, 'wordpress');
      const htmlFile = [join(wpDir, 'preview.html'), join(wpDir, 'content.html')].find((f) =>
        existsSync(f),
      );
      if (htmlFile) {
        await page.goto(pathToFileURL(htmlFile).href, { waitUntil: 'load' });
      } else {
        const renderPhp = join(wpDir, 'render.php');
        if (existsSync(renderPhp)) {
          const html = `<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><link rel="stylesheet" href="${pathToFileURL(join(wpDir, 'style.css')).href}"></head><body>${readFileSync(renderPhp, 'utf-8').replace(/<\?php[\s\S]*?\?>/g, '')}</body></html>`;
          const previewPath = join(wpDir, 'preview.html');
          writeFileSync(previewPath, html);
          await page.goto(pathToFileURL(previewPath).href, { waitUntil: 'load' });
        }
      }
    }

    await settlePage(page);
    await page.screenshot({ path: currentPath, fullPage: true, animations: 'disabled' });
    await page.close();

    if (update || !existsSync(baselinePath)) {
      copyFileSync(currentPath, baselinePath);
      results.push({
        viewport: vp.name,
        passed: true,
        action: 'baseline_updated',
        diffPixels: 0,
        diffPercent: 0,
      });
      continue;
    }

    try {
      const cmp = compareImages(baselinePath, currentPath, diffPath, opts);
      results.push({ viewport: vp.name, ...cmp });
    } catch (e) {
      // pngjs / pixelmatch 失敗時はバイト比較フォールバック
      const current = readFileSync(currentPath);
      const baseline = readFileSync(baselinePath);
      const passed = current.equals(baseline);
      if (!passed) copyFileSync(currentPath, diffPath);
      results.push({
        viewport: vp.name,
        passed,
        diffPixels: Math.abs(current.length - baseline.length),
        reason: `fallback: ${e.message}`,
      });
    }
  }

  await browser.close();

  const passed = results.every((r) => r.passed);
  const report = {
    session_id: sessionId,
    passed,
    results,
    base_url: baseUrl || 'local',
    thresholds: opts,
    compared_at: new Date().toISOString(),
  };
  writeFileSync(join(sessionDir, 'visual_regression.json'), JSON.stringify(report, null, 2));

  console.log(`VISUAL REGRESSION ${passed ? 'PASSED' : 'FAILED'}: ${sessionId}`);
  for (const r of results) {
    const extra =
      r.action ||
      (r.diffPercent != null ? `${r.diffPercent}%` : '') ||
      r.reason ||
      '';
    console.log(`  [${r.passed ? 'OK' : 'NG'}] ${r.viewport} ${extra}`);
  }
  process.exit(passed ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
