---
name: bootstrapping-projects
description: Use when the user wants to scaffold, bootstrap, or generate a new small-to-medium project (under ~50 files) and expects working code, not just a sketch. Triggers on "build me a [tool/app/service]...", "scaffold a project", "create a starter/boilerplate/template for...", "init a new [stack] project", "kickstart a project". Not for single-file scripts, modifications to existing projects, or architecture discussions.
---

# Bootstrapping Projects

Generate a working software project from a natural-language description, via a
four-stage pipeline: bootstrap → expand → verify → revise.

## Quick Reference

| Stage | Prompt file | Input | Output | Human checkpoint |
|-------|------------|-------|--------|:----------------:|
| 1. Bootstrap | `prompts/bootstrap.md` | User description | Contract (assumptions, tree, manifest, data model, README, representative files, configs) | Yes — review before expand |
| 2. Expand | `prompts/expand.md` | Bootstrap output + target file list | Full project files + NOTES/FLAGS | No |
| 3. Verify | `scripts/harness.py` + `prompts/triage.md` | Project on disk | JSON failure report → triage → revise loop (max 5 iterations) | Yes — review verified project |
| 4. Revise | `prompts/revise.md` | Bootstrap + project + change request | File diffs + CONTRACT IMPACT | No (re-runs verify) |

## When to use this skill

Trigger when the user wants to scaffold a new software project from a
description and expects working code, not just a sketch. Phrases like:

- "Build me a [tool/app/service/CLI] that..."
- "Generate a project for..."
- "Scaffold a [stack] project that does..."
- "I want to start a project that..."
- "Create a starter/boilerplate/template for..."
- "Init a new [stack] project"
- "Kickstart a [tool/app] that..."

Do NOT use this skill for:

- Single-file scripts or snippets — just write the code.
- Modifications to an existing project — use normal coding workflow.
- Architecture discussions, design questions, or "how would I build X" —
  the user wants thinking, not files.
- Projects larger than ~50 files. This pipeline is designed for small
  projects. For larger ones, scaffold the core and let the user request
  expansions.

## The four stages

Each stage has a dedicated prompt in `prompts/`. **Read the relevant prompt's
contents before running that stage** — do not run a stage from memory.

1. **Bootstrap** (`prompts/bootstrap.md`) — Description → contract.
   Produces assumptions, file tree, dependency manifest, data model, README,
   one or two representative files, key configs. The contract is small
   enough for a human to review in five minutes.

2. **Expand** (`prompts/expand.md`) — Contract → full project.
   Generates every remaining file in the tree, in dependency order, leaves
   first. Treats the bootstrap as immutable. Emits `## NOTES` for
   compromises and observations, `## FLAGS` only for true blockers.

3. **Verify** (`scripts/harness.py` + `prompts/triage.md`) — Project →
   verified project. Runs install, typecheck, lint, build, test against the
   project on disk. Failures get triaged into a change request and routed
   through the reviser. Loops until green, stuck, or capped.

4. **Revise** (`prompts/revise.md`) — Project + change request → diff.
   Used both by the verify loop (driven by triage output) and by the user
   for post-generation changes. Whole-file replacement, not patches.
   Surfaces `CONTRACT IMPACT` when a change requires updating the bootstrap.

## How to run the pipeline

Human-in-the-loop at two points: after bootstrap (review the contract) and
after verify (review the working project). Verify runs automatically with
bounded recovery.

### Stage 1 — Bootstrap

1. Read `prompts/bootstrap.md`.
2. Render the prompt with the user's description in `{{DESCRIPTION}}`.
3. Produce the bootstrap output. Show it to the user.
4. Wait for approval. If the user requests changes to assumptions or the
   tree, regenerate or hand-edit the bootstrap before proceeding. Do NOT
   proceed to stage 2 until the user approves.

### Stage 2 — Expand

1. Read `prompts/expand.md`.
2. Compute the target file list: every file in the tree minus what
   bootstrap already produced (representative files, manifest, schema,
   README, configs in section 8).
3. If the target list is more than ~10 files, batch it. Within each batch,
   group by dependency layer (leaves → utilities → domain → interface →
   entry points). Pass earlier batches' contents as context to later
   batches so imports resolve.
4. For each batch: render the prompt with `{{BOOTSTRAP_OUTPUT}}` set to
   the bootstrap plus all previously-generated files, and `{{TARGETS}}`
   set to the batch's file list.
5. Parse the output. Each file is delimited by `### path/to/file.ext`
   followed by a fenced code block. Write each to disk under the project
   root.
6. Accumulate `## NOTES` across batches.
7. If any batch returns `## FLAGS`, stop. Surface to the user. Resume from
   the failed batch after they edit the bootstrap.

### Stage 3 — Verify

1. Run `python scripts/harness.py <project-root>`. The harness detects the
   stack from the manifest, runs install/typecheck/lint/build/test in
   order, and emits a JSON failure report.
2. If `all_passed: true`: stage 3 done. Surface project + accumulated
   notes to the user.
3. If checks fail: enter the verify loop.
   - Read `prompts/triage.md`.
   - Render with `{{HARNESS_REPORT}}` and `{{BOOTSTRAP}}`.
   - Triage produces one of: `## REQUEST` + `## SCOPE` (run reviser),
     `## CONTRACT FIX NEEDED` (escalate to user), `## CANNOT FIX` (halt).
   - On REQUEST: read `prompts/revise.md`, render with the bootstrap,
     current project state, the request, and the scope. Apply the diff
     to disk.
   - Re-run the harness. Compare reports.
4. Loop bounds (enforce strictly):
   - Max 5 iterations.
   - No-progress: same failure set two iterations in a row → halt.
   - Regression: more new failures than fixed failures → roll back the
     last revision, halt.
   - Token budget: ~200k tokens across all triage + revise calls per loop.
5. On halt for any reason other than convergence: surface the transcript
   (report → triage → diff → next report) so the user can take over.

### Stage 4 — Revise (user-driven)

After the user has a verified project, they may request changes.

1. Read `prompts/revise.md`.
2. Render with the bootstrap, the full current project, the user's
   request. Do not pass a SCOPE — the user-driven path lets the reviser
   pick scope based on the request.
3. Apply the diff. Re-run stage 3 (verify) on the modified project.
4. If the diff's `## CONTRACT IMPACT` is `BREAKING` or `ADDITIVE`: surface
   to the user. They decide whether to update the bootstrap.

## Template Variables

| Variable | Prompt | Binds to |
|----------|--------|----------|
| `{{DESCRIPTION}}` | `bootstrap.md` | The user's natural-language project description |
| `{{BOOTSTRAP_OUTPUT}}` | `expand.md` | Full bootstrap output + any files from earlier expand batches |
| `{{TARGETS_OR_EMPTY}}` | `expand.md` | File paths to generate in this batch (empty = all remaining) |
| `{{HARNESS_REPORT}}` | `triage.md` | JSON failure report from `harness.py` |
| `{{BOOTSTRAP}}` | `triage.md`, `revise.md` | The original bootstrap contract |
| `{{PROJECT}}` | `revise.md` | Current state of all project files |
| `{{REQUEST}}` | `revise.md` | Change request (from triage or user) |
| `{{SCOPE_OR_EMPTY}}` | `revise.md` | Comma-separated file paths the reviser may touch (empty = reviser picks) |

## Output conventions

- All file outputs use `### path/to/file.ext` headers followed by fenced
  code blocks. The path is relative to the project root.
- The project root is created in the user's working directory unless they
  specify otherwise. Default name is derived from the bootstrap's project
  name.
- After each stage, surface a short status to the user: stage name, what
  ran, what's next, what they need to do.

## Failure handling

- **Bootstrap fails** (description too vague): the prompt asks up to 3
  clarifying questions. Pass them to the user. Resume bootstrap with
  answers.
- **Expand returns FLAGS**: bootstrap has an inconsistency. Surface to
  the user; do not attempt to fix in-place. Common cause: representative
  file uses a library not in the manifest.
- **Verify halts on no-progress or regression**: structural problem in
  the expand output. Surface the transcript; offer to regenerate the
  affected files from scratch with an updated bootstrap (often cleaner
  than continuing to revise).
- **Revise returns FLAGS**: ambiguity in the request. Pass the
  clarification question to the user.
- **Triage returns CANNOT FIX**: the harness is hitting an environment
  issue (network, real DB, real auth). Note it and proceed without that
  check.

## Style and conventions

- Floor version pins in manifests (`>=`, `^`, `~>`) unless verified.
- Bootstrap fits in one human review (target: under 400 lines including
  representative file).
- Generated code matches the representative file's style — error handling,
  logging, imports, naming. The expand prompt enforces this; verify it
  on spot-check.
- No drive-by changes during revise. Diffs touch only what the request
  requires.

## Stack support

The harness supports these stacks out of the box:

- TypeScript / Node (npm, detected from `package.json` + `tsconfig.json`)
- JavaScript / Node (npm, detected from `package.json` without TS config)
- Python (uv preferred, falls back to pip)
- Rust (cargo)
- Go (go modules)

For other stacks, the harness emits `stack: unknown` and the verify stage
skips. Bootstrap and expand still work; the user runs their own
verification.

## Examples

See `examples/standup-bot.md` for a worked end-to-end run: a Slack bot for
GitHub digests, from description to verified project. Read it before the
first generation in a session — it calibrates the level of detail the
bootstrap and expand stages should produce.
