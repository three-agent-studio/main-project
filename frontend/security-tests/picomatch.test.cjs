const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFileSync, realpathSync } = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const frontend = path.resolve(__dirname, '..');
const vendor = path.join(frontend, 'vendor/picomatch');
const picomatch = require('picomatch');

test('every locked picomatch consumer resolves to the private, patched copy', () => {
  const lock = require('../package-lock.json');
  const entries = Object.entries(lock.packages).filter(([key]) => /(^|\/)node_modules\/picomatch$/.test(key));
  assert.equal(entries.length, 1, 'no nested vulnerable registry copy may remain');
  assert.equal(entries[0][1].resolved, 'vendor/picomatch');
  assert.equal(entries[0][1].link, true);
  assert.equal(realpathSync(require.resolve('picomatch')), path.join(vendor, 'index.js'));
  assert.equal(require('picomatch/package.json').name, '@digital-deanery/picomatch');
  for (const consumer of ['tinyglobby', 'vite', 'vitest', 'fdir']) {
    const consumerFile = require.resolve(consumer);
    const resolved = require.resolve('picomatch', { paths: [path.dirname(consumerFile)] });
    assert.equal(realpathSync(resolved), path.join(vendor, 'index.js'), consumer);
  }
});

test('vendored files retain upstream provenance and the reviewed parser patch', () => {
  const manifest = require('../vendor/picomatch/UPSTREAM.json');
  for (const [file, originalHash] of Object.entries(manifest.originalSha256)) {
    const actual = createHash('sha256').update(readFileSync(path.join(vendor, file))).digest('hex');
    assert.equal(actual, manifest.patchedSha256[file] || originalHash, file);
  }
});

test('repeated extglobs are literals across public compilation paths', () => {
  for (const entry of [picomatch, require('picomatch/posix')]) {
    for (const options of [{}, { fastpaths: false }, { capture: true }, { maxExtglobRecursion: false }]) {
      for (const pattern of ['+(a)', '*(a)', '+(*)', '+(*a)', '*(a*)', '+(a|aa)', '+(+(a))']) {
        const regex = entry.makeRe(pattern, options);
        assert.equal(regex.test(pattern), true, `literal ${pattern}`);
        assert.equal(regex.test('aaaa'), false, `not repetition ${pattern}`);
        assert.equal(entry.compileRe(entry.parse(pattern, options), options).test('aaaa'), false);
        assert.equal(entry(pattern, options)('aaaa'), false);
      }
    }
  }
});

test('adversarial repeated extglobs finish within a hard process deadline', () => {
  // Never run a potentially regressed ReDoS in the test runner itself. A timeout
  // kills the child even if RegExp blocks the event loop; test timeouts cannot.
  const probe = `
    const assert = require('node:assert/strict');
    for (const pm of [require('picomatch'), require('picomatch/posix')]) {
      for (const options of [{}, { fastpaths: false }, { maxExtglobRecursion: false }]) {
        for (const pattern of ['+(*a)', '+(*)b', '*(*)b', '*(a*)b', '+(*?a)', '+(+(a*))b', '?(*(+(*a)))b', 'x/+(*a).ts']) {
          const input = (pattern.startsWith('x/') ? 'x/' : '') + 'a'.repeat(4000) + '!';
          assert.equal(pm(pattern, options)(input), false, pattern);
          assert.equal(pm.makeRe(pattern, options).test(input), false, pattern);
          assert.equal(pm.compileRe(pm.parse(pattern, options), options).test(input), false, pattern);
        }
      }
    }
  `;
  const result = spawnSync(process.execPath, ['-e', probe], {
    cwd: frontend, timeout: 3000, killSignal: 'SIGKILL', encoding: 'utf8',
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
});

test('ordinary project globs, optional extensions and ignore filters remain usable', () => {
  const cases = [
    ['src/**/*.{ts,tsx}', 'src/features/student/ScheduleWeek.tsx', true],
    ['src/**/*.{ts,tsx}', 'src/styles.css', false],
    ['**/*.{test,spec}.?(c|m)[jt]s?(x)', 'src/schedule.test.ts', true],
    ['**/*.{test,spec}.?(c|m)[jt]s?(x)', 'src/login.spec.tsx', true],
    ['**/*.{test,spec}.?(c|m)[jt]s?(x)', 'src/login.ts', false],
    ['**/!(*.d).ts', 'src/main.ts', true],
    ['**/!(*.d).ts', 'src/global.d.ts', false],
    ['**/@(index|main).ts', 'src/main.ts', true],
  ];
  for (const [glob, input, expected] of cases) assert.equal(picomatch(glob)(input), expected, glob);
  const match = picomatch('**/*.ts', { ignore: ['**/node_modules/**', '**/.git/**'], dot: true });
  assert.equal(match('src/main.ts'), true);
  assert.equal(match('node_modules/example/main.ts'), false);
  assert.equal(match('.git/main.ts'), false);
  assert.equal(picomatch.scan('src/**/*.ts').isGlob, true);
});
