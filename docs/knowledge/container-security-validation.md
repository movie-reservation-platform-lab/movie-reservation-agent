# Agent container security validation

Validated locally on 2026-09-15 for issue #15 / PR #17.

## Implementation and dependencies

- Shared preparation, evidence and PR scanner use reviewed commit
  `bb40579c285df0b581c48b10f9b34574d5c78639`, merged in
  [actions #13](https://github.com/movie-reservation-platform-lab/movie-platform-actions/pull/13).
- References: merged [recommendation-MCP #11](https://github.com/movie-reservation-platform-lab/movie-recommendation-mcp/pull/11)
  and [reservation-MCP #9](https://github.com/movie-reservation-platform-lab/movie-reservation-mcp/pull/9).
- [Environments #82](https://github.com/movie-reservation-platform-lab/movie-platform-environments/issues/82)
  owns v3 consumption and independent current-policy admission. PR diagnostics
  are not signed evidence. Fresh canonical publication is required after merge.

## Agent-specific findings

The baseline Bookworm image failed with **6 CRITICAL / 79 HIGH**: SQLite
CVE-2025-7458, Perl CVE-2026-13221 / CVE-2026-42496 / CVE-2026-8376,
zlib CVE-2023-45853, and Authlib CVE-2026-27962.

The final Trixie image passes with **0 CRITICAL / 44 HIGH / 48 MEDIUM / 57 LOW /
1 UNKNOWN**, zero exemptions. All remaining findings are OS packages with no
fixed version listed in this report; Python packages have zero findings.
These are the agent's own results, not copied sibling counts. HIGH remains
non-blocking under current producer policy and visible for downstream review.

Remediation:

- Separate build tooling from runtime, copy only the installed non-editable
  environment, replace curl health check with Python and remove system pip.
- Refresh `perl-base`, `gzip`, `libc-bin`, `libc6`, `libpcre2-8-0`, and
  `libsqlite3-0` to available Debian fixes.
- Update scan-identified Python packages: Authlib 1.8.0, cryptography 50.0.1,
  Black 26.5.1 (a Piccolo transitive dependency), Pygments 2.21.0, idna 3.19,
  python-dotenv 1.2.3, FastAPI 0.141.1 and Starlette 1.6.0.
- Update OpenTelemetry SDK/API/exporter to 1.44.0 and instrumentation to 0.65b0
  for compatibility with FastAPI's included routers. The initial test failure
  and full diagnostics were retained; the compatible versions pass existing
  route, audit correlation and trace tests without application-code changes.

Primary references: [Authlib advisory](https://github.com/authlib/authlib/security/advisories/GHSA-wvwj-cvrp-7pv5),
[OpenTelemetry compatibility fix](https://github.com/open-telemetry/opentelemetry-python-contrib/pull/4700),
[Debian Perl](https://security-tracker.debian.org/tracker/CVE-2026-13221),
[SQLite](https://security-tracker.debian.org/tracker/CVE-2025-7458),
[zlib](https://security-tracker.debian.org/tracker/CVE-2023-45853).

## Validation and retained diagnostics

- Frozen pytest: **88 passed** (78 runtime, 10 automation); three existing
  Pydantic/Authlib deprecation warnings remain.
- Exact scoped CI Ruff lint/format and compile checks passed; shell syntax and
  Git diff whitespace checks passed.
- Built the agent's `linux/amd64` production target, exercised health and the
  full recommendation/catalog/request/status workflow through local MCP fakes,
  and verified correlation fields and UID 10001.
- Verified installed imports come from `/venv`, absence of uv/uvx/curl/pip,
  pytest/Ruff and `/app` source, and the Python health-check command.
- Failure-path tests verify original exit status, response/error body and
  container/fake logs survive failed container start and failed HTTP request.
- Shared Trivy 0.70.0 scan decision: **passed** at `2026-09-15T08:09:54Z`, current
  central policy revision `bb40579c285df0b581c48b10f9b34574d5c78639`.
- Local image ID: `sha256:a4106b7eb0296090e31eca9ca84e895b36439db6f600d89dcf9865cf77389e04`.
- Complete report SHA-256: `c1afcda5d1d71a4d8bb0e5c71d7901a3fe73a1ce8d10ff6c6d3efb08dc4d54d3`.

Complete baseline, intermediate and final reports, policy JSON, build output,
failed/passing tests, and smoke diagnostics remain in the issue worktree's
ignored `.local-container-security/` directory. Final report:
`.local-container-security/final/run-B9U7sB/vulnerabilities.json`.
Hosted workflows upload the full PR scan/smoke directories for 14 days after
failure as well as success. Explicit Bash pipefail prevents diagnostic `tee`
commands from hiding failed builds/scans. Tokens are scoped to evaluation and
are not written to reports.

The original checkout and its uncommitted files remain intact. The issue branch
includes its canonical `.ai` skills and documentation changes, reconciled with
current demo documentation. Generated assistant directories and `AGENTS.md`
remain on disk but are untracked/ignored; regenerate them with `.ai/sync.sh`.

No merge, canonical image publication, workflow dispatch, exemption request,
environment admission or AWS change is part of this validation.

## KB used

`/home/patex1987/Documents/programming_kb/patterns/Multi-Stage Python Container Builds with uv.md`
informed compatible interpreter bases, isolated tooling and installed-image smoke.
