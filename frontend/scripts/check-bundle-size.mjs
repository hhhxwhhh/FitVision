#!/usr/bin/env node
/** Validates dist/ against gzip budgets to prevent bundle-size regressions. */
import { gzipSync } from 'node:zlib'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'

const distDir = resolve(process.argv[2] || 'dist')

// Budgets are intentionally above current sizes with headroom, but far below
// the pre-optimisation numbers (element-plus 898KB, echarts 1134KB).
const budgets = [
  { name: 'initial entry chunk', match: (f) => /^assets\/index-[\w-]+\.js$/.test(f), maxKb: 40 },
  { name: 'critical-path CSS', match: (f) => /^assets\/index-[\w-]+\.css$/.test(f), maxKb: 80 },
  { name: 'any single JS chunk', match: (f) => f.endsWith('.js'), maxKb: 450 },
]

const gzipKb = (file) => gzipSync(readFileSync(file)).length / 1024

const collectAssets = (dir) => {
  const found = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) {
      found.push(...collectAssets(path))
    } else if (/\.(js|css)$/.test(entry.name) && !entry.name.endsWith('.map')) {
      found.push(path)
    }
  }
  return found
}

const assets = collectAssets(distDir)
  .map((file) => ({
    name: file.slice(distDir.length + 1),
    file,
    kb: gzipSync(readFileSync(file)).length / 1024,
  }))
  .sort((a, b) => b.kb - a.kb)

const failures = []

if (assets.length === 0) {
  console.error('No built assets found. Run `npm run build` first.')
  process.exit(1)
}

for (const budget of budgets) {
  for (const asset of assets.filter((a) => budget.match(a.name))) {
    if (asset.kb > budget.maxKb) {
      failures.push(`${budget.name}: ${asset.name} is ${asset.kb.toFixed(1)}KB gzip (budget ${budget.maxKb}KB)`)
    }
  }
}

const totalKb = assets.reduce((sum, a) => sum + a.kb, 0)
const jsKb = assets.filter((a) => a.name.endsWith('.js')).reduce((sum, a) => sum + a.kb, 0)
const cssKb = assets.filter((a) => a.name.endsWith('.css')).reduce((sum, a) => sum + a.kb, 0)

console.log('Bundle report (gzip)')
console.log(`  assets   : ${assets.length}`)
console.log(`  JS total : ${jsKb.toFixed(1)}KB`)
console.log(`  CSS total: ${cssKb.toFixed(1)}KB`)
console.log(`  combined : ${totalKb.toFixed(1)}KB`)

if (failures.length > 0) {
  console.error('\nBundle budget exceeded:')
  for (const failure of failures) console.error(`  - ${failure}`)
  process.exit(1)
}

console.log('\nBundle budgets OK.')
