# Worked example: standup-bot

A condensed end-to-end run of the four-stage pipeline. Use this as
calibration for the level of detail each stage should produce.

## User description

> A Slack bot for engineering teams that watches a configured set of GitHub
> repos and posts a daily standup digest to a channel: PRs opened, PRs
> merged, PRs that have been waiting on review for >24 hours, and CI
> failures on main. Configurable per channel — different channels can watch
> different repo sets. Should not duplicate-post if it crashes and restarts.

## Stage 1 — Bootstrap (abridged)

The bootstrap produced ~350 lines covering:

- **Assumptions** (8 bullets): TypeScript + Bolt + Octokit + Drizzle on
  Postgres; Socket Mode; per-channel config in DB managed via slash
  commands; GitHub App auth; idempotency via `digest_runs (channel_id,
  digest_date)` PK; "stale >24h" defined as open + reviewer-requested +
  no approval + last activity 24h+; CI via Checks API on default branch;
  IANA timezones at 09:00 local default.

- **File tree** (15 paths): `src/index.ts`, `src/config.ts`,
  `src/logger.ts`, `src/db/{client,schema}.ts`,
  `src/slack/{app,commands,format}.ts`, `src/github/{client,queries}.ts`,
  `src/digest/{build,post,schedule}.ts`, `src/types.ts`, plus configs.

- **Manifest**: `package.json` with `@slack/bolt`, `@octokit/app`,
  `@octokit/rest`, `drizzle-orm`, `postgres`, `node-cron`, `luxon`,
  `zod`, `pino`. Floor pins.

- **Data model**: Drizzle schema in `src/db/schema.ts` with four tables —
  `channel_configs`, `watched_repos`, `digest_runs`, `github_installations`.
  PK on `digest_runs` is `(channel_id, digest_date)` — that's the
  idempotency lock.

- **Representative file**: `src/digest/post.ts`. Uses `db.transaction`
  with `SELECT ... FOR UPDATE` to claim the row, then posts to Slack,
  then updates the row with the message ts. On error, marks the row
  failed and rethrows. This pinned the project's style: child loggers
  via `logger.child({ ... })`, Drizzle `eq`/`and` imports, error-then-
  rethrow pattern.

- **README** with primary user flow walkthrough naming `schedule.ts`,
  `build.ts`, `post.ts`, and the idempotency model.

## Stage 2 — Expand

Targets after subtracting bootstrap output: 13 files. Single batch was
fine (under the 10-file batching threshold the SKILL.md mentions, but
13 is close — borderline acceptable for a single call, would split to
two batches if any file were larger).

Generation order followed leaves-first:

1. `src/types.ts` — pure types, no internal imports.
2. `src/logger.ts`, `src/config.ts`, `tsconfig.json`, `drizzle.config.ts`,
   `.gitignore`, `drizzle/.gitkeep` — utilities and configs.
3. `src/db/client.ts` — depends on config and schema.
4. `src/github/client.ts`, `src/github/queries.ts` — domain.
5. `src/slack/format.ts`, `src/digest/build.ts`, `src/digest/schedule.ts`,
   `src/slack/commands.ts` — interface + domain.
6. `src/slack/app.ts`, `src/index.ts` — entry points last.

Output had a `## NOTES` section with one [COMPROMISE] entry (the
bootstrap's `digestRuns.statusIdx` was a redundant `uniqueIndex` that
would have prevented status transitions; the expander used the PK for
idempotency claims and noted it for the reviewer) and three
observations (CommonJS Bolt import quirk, hot path in `fetchStalePRs`,
scheduler granularity).

## Stage 3 — Verify (loop, 2 iterations)

### Iteration 1

Harness report (abridged):

```json
{
  "stack": "typescript-node",
  "checks": [
    {"name": "install", "status": "pass", "duration_ms": 8400},
    {"name": "typecheck", "status": "fail", "duration_ms": 3200,
     "failures": [
       {"file": "src/digest/build.ts", "line": 47, "code": "TS2322",
        "message": "Type 'PullRequestSummary[]' is not assignable to type 'never[]'."},
       {"file": "src/digest/build.ts", "line": 48, "code": "TS2322",
        "message": "Type 'MergedPullRequestSummary[]' is not assignable to type 'never[]'.  [×3 occurrences]"}
     ]},
    {"name": "lint", "status": "skipped", "reason": "blocked by upstream failure"},
    {"name": "build", "status": "skipped", "reason": "blocked by upstream failure"},
    {"name": "test", "status": "skipped", "reason": "blocked by upstream failure"}
  ],
  "all_passed": false
}
```

Triage output:

```
## REQUEST

In src/digest/build.ts, the four accumulator arrays (opened, merged,
stale, ciFailures) are declared as `const x = []`, which TypeScript
infers as `never[]`. Add explicit type annotations using the types
already defined in src/types.ts: PullRequestSummary[],
MergedPullRequestSummary[], StalePullRequestSummary[], CiFailureSummary[].

## SCOPE

src/digest/build.ts
```

Reviser produced a one-file MODIFY adding the four type annotations.
CONTRACT IMPACT: NONE.

### Iteration 2

Harness re-run: all checks pass. (No tests in the project — `npm test
--if-present` succeeds silently when no test script exists.)

Loop converged in 2 iterations, well within the 5-iteration cap.

## Stage 4 — Revise (not exercised in this example)

User accepted the verified project. No revision requests.

## What this example calibrates

- **Bootstrap length**: ~350 lines is the right size. Longer means
  scope creep; shorter means missing decisions.
- **Tree size**: 15 files is comfortable. Above ~25 files the bootstrap
  starts to feel sparse and you should consider whether the project
  should be split.
- **Notes density**: 4 entries (1 compromise + 3 observations) for a
  13-file expand is realistic. Zero notes is suspicious; more than ~8
  per batch suggests the bootstrap was underspecified.
- **Verify iterations**: 1–3 iterations is normal. Hitting 5 is a
  signal something is structurally wrong, not just typo'd.
- **Triage scope**: 1–3 files in SCOPE is normal for a typecheck
  failure. Wider scope means the failure is structural and should
  probably be a CONTRACT FIX NEEDED.
