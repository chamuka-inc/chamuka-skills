# chamuka-skills

A Claude Code plugin of reusable agent skills. Skills live in `skills/<skill-name>/SKILL.md`.

All skills **must** conform to the [Agent Skills specification](https://agentskills.io/specification). Read it before creating or reviewing a skill. The guidelines below are our opinionated layer on top of the spec.

## Skill Structure

```
skills/
  my-skill/
    SKILL.md              # required
    scripts/              # optional: executable code
    references/           # optional: detailed documentation
    assets/               # optional: templates, schemas, resources
```

Flat namespace — no nesting. Directory name must match the `name` frontmatter field.

## Our Style Guide (on top of the spec)

### Naming

Prefer gerund form: `processing-pdfs` not `pdf-processor`, `managing-databases` not `database-management`.

### Descriptions

The spec allows up to 1024 characters. We target ≤500 to stay concise.

- Start with "Use when..." to focus on triggering conditions
- Describe the problem/situation, NOT what the skill does or its workflow
- Include concrete triggers: error messages, symptoms, tool names
- Technology-agnostic unless the skill itself is technology-specific

```yaml
# BAD: summarizes workflow — agents follow this instead of reading the skill
description: Use when debugging — collects logs, bisects commits, and writes regression tests

# BAD: vague
description: Helps with testing

# GOOD: triggering conditions only
description: Use when tests have race conditions, timing dependencies, or pass/fail inconsistently
```

### Body Structure

The spec has no format restrictions. We recommend:

```markdown
# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Symptoms and use cases (bullet list). When NOT to use.

## Core Pattern
Before/after comparison or key steps.

## Quick Reference
Table or bullets for scanning common operations.

## Common Mistakes
What goes wrong and how to fix it.
```

### Token Budget

Keep SKILL.md under 500 lines / ~5000 tokens. Reference other files with relative paths, one level deep from SKILL.md. Push heavy content into `references/`, `scripts/`, or `assets/`.

## Writing Principles

**Concise is key.** Every token competes for context window space.

**Assume Claude is smart.** Only add context Claude doesn't already have.

**Set appropriate degrees of freedom:**
- High freedom (guidelines) — when multiple approaches are valid
- Medium freedom (pseudocode) — when a preferred pattern exists
- Low freedom (exact commands) — when operations are fragile and sequence matters

**Keyword coverage for discovery.** Include error messages, symptoms, synonyms, tool names, and file types that agents would search for.

## When NOT to Create a Skill

- **One-off solutions** — not reusable across projects
- **Project-specific conventions** — belong in that project's CLAUDE.md
- **Standard practices** — well-documented elsewhere, Claude already knows them
- **Mechanical constraints** — enforceable by automation (hooks, linters, CI)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Description summarizes workflow | Describe only triggering conditions |
| Name doesn't match directory | Spec requires `name` = directory name |
| Uppercase or `--` in name | Lowercase, single hyphens only |
| Vague name ("helper", "utils") | Use specific gerund form |
| Over-explaining known concepts | Delete anything Claude already knows |
| Missing keyword coverage | Add error messages, symptoms, synonyms |
| SKILL.md over 500 lines | Split to `references/`, `scripts/`, `assets/` |
| Deep file reference chains | Keep references one level deep |
