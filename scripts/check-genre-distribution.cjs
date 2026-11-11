const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(path.join(__dirname, '../utils/genres.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } });
const exportsObject = {};
vm.runInNewContext(compiled.outputText, { exports: exportsObject });

const rows = exportsObject.getGenreDistribution({
  2025: [
    { genres: 'historical fiction' },
    { genres: 'mystery' },
    { genres: '' },
    { genres: '', Type: 'Non-fiction' },
  ],
  2026: [
    { genres: 'horror' },
    { genres: 'biography' },
    { genres: 'coming-of-age' },
    { Genre: 'romance' },
  ],
});

assert.equal(rows[0].Historical, 25);
assert.equal(rows[0]['Mystery & Thriller'], 25);
assert.equal(rows[0].Uncategorized, 25);
assert.equal(rows[0]['Non-Fiction'], 25);
assert.equal(rows[1].Speculative, 25);
assert.equal(rows[1].Literary, 25);
assert.equal(rows[1].Romance, 25);
for (const row of rows) {
  const total = Object.entries(row).filter(([key]) => key !== 'year').reduce((sum, [, value]) => sum + value, 0);
  assert.ok(Math.abs(total - 100) < 1e-8);
}
console.log('Genre distribution checks passed');
