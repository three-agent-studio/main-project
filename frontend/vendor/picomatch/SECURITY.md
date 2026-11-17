# Private picomatch security fork

This directory contains the MIT-licensed runtime sources of picomatch 4.0.7.
The original copyright and LICENSE are preserved. UPSTREAM.json records the
source, original SHA-256 hashes and the patched parser hash. The private package
name and `+deanery.1` version metadata identify our fork, not an upstream release.

## Why this copy exists

[GHSA-fc5q-39xc-vjpf / CVE-2026-112366](https://github.com/advisories/GHSA-fc5q-39xc-vjpf)
affects upstream versions through 4.0.7. On 2026-11-17 the reviewed advisory lists
no fixed release. Repeated single-branch extglobs such as `+(*a)` can produce
nested unbounded regular-expression quantifiers and exponential backtracking.
The existing recursion limit does not cover this case.

## Deliberate compatibility restriction

In `lib/parse.js`, `extglobClose` sends **every** `+(...)` and `*(...)` extglob
through the existing literal-escaping fallback. Even simple repeated extglobs
are treated as literal filenames. This applies with or without
`maxExtglobRecursion: false`; callers cannot opt back into the vulnerable path.
For example, `+(a)` matches the literal `+(a)`, not `aaa`.

Ordinary `*`, `**`, `?`, character classes, braces and optional/negated/`@`
extglobs remain available. The public module entry points and APIs are preserved.
This is a conservative grammar restriction, not a general guarantee that arbitrary
regular expressions or every possible glob are safe. `toRegex`, `test`,
`compileRe` with hand-crafted state, and `regex: true` must still receive trusted
regex input, just as in upstream. Do not expose them as an untrusted-regex API.

The project uses this library in development/build tools, not in the deployed
Django server. The application does not require repeated extglobs. Before adding
new build patterns, check whether they rely on that restricted syntax.

## Installation and verification

The frontend's explicit file devDependency and `$picomatch` npm override route
all transitive consumers to this directory. Keep both entries and the generated
lockfile together. Do not replace this with an audit exclusion, an invented
upstream version, or a postinstall modification.

`npm run test:security` checks the installed resolution, source provenance,
literal behavior and long adversarial inputs in processes with hard deadlines.
CI runs these tests, the unchanged `npm audit --audit-level=moderate`, lint,
unit tests, production build and browser tests. Audit alone cannot evaluate our
private patch; the behavioral regressions are essential.

When a verified official fix is available, test it against these regressions
and the full frontend suite, then remove the override, explicit dependency and
vendor directory in one change. Until then, any parser changes need explicit
review and an updated provenance hash. Upstream dependency monitoring remains
necessary even though npm does not know the private fork's advisory history.
