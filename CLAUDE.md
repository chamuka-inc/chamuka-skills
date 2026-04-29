# chamuka-skills

A Claude Code plugin of reusable agent skills. Skills live in `skills/<skill-name>/SKILL.md`.

## Skill Structure

Each skill is a directory under `skills/` containing:

- `SKILL.md` (required) — main skill document
- Supporting files (optional) — only when content exceeds ~100 lines or is a reusable script/template

```
skills/
  my-skill/
    SKILL.md
    reference.md        # optional: heavy reference material
    helper-script.sh    # optional: reusable tooling
```

Flat namespace — no nesting of skill directories.

## SKILL.md Format

### Frontmatter (required)

```yaml
---
name: skill-name-with-hyphens
description: Use when [specific triggering conditions, symptoms, and contexts]
---
```

**`name`:** Letters, numbers, and hyphens only. Prefer gerund form:
- `processing-pdfs` not `pdf-processor`
- `managing-databases` not `database-management`

**`description`:** Max 500 characters. Rules:
- Third person ("Processes..." not "I process...")
- Start with "Use when..." to focus on triggering conditions
- Describe the problem/situation, NOT what the skill does or its workflow
- Include concrete triggers: error messages, symptoms, tool names
- Technology-agnostic unless the skill itself is technology-specific

```yaml
# BAD: summarizes workflow — agents will follow this instead of reading the skill
description: Use when debugging — collects logs, bisects commits, and writes regression tests

# BAD: vague
description: Helps with testing

# GOOD: triggering conditions only
description: Use when tests have race conditions, timing dependencies, or pass/fail inconsistently
```

### Body

```markdown
# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Symptoms and use cases (bullet list).
When NOT to use.

## Core Pattern
Before/after comparison or key steps.

## Quick Reference
Table or bullets for scanning common operations.

## Common Mistakes
What goes wrong and how to fix it.
```

Keep SKILL.md under 500 lines. Move heavy reference (API docs, syntax guides) to separate files and reference them from SKILL.md.

## Writing Principles

**Concise is key.** The context window is shared with the system prompt, conversation history, other skills, and the user's request. Every token in your skill competes for space. Challenge each line: does Claude really need this?

**Assume Claude is smart.** Only add context Claude doesn't already have. Don't explain what PDFs are. Don't explain how libraries work. Show the specific knowledge that isn't obvious.

**Progressive disclosure.** SKILL.md is the overview — point to detailed files as needed, like a table of contents. Claude reads SKILL.md first and pulls in supporting files only when relevant.

**Set appropriate degrees of freedom:**
- High freedom (guidelines) — when multiple approaches are valid
- Medium freedom (pseudocode) — when a preferred pattern exists
- Low freedom (exact commands) — when operations are fragile and sequence matters

**Keyword coverage for discovery.** Include terms Claude would search for:
- Error messages: "ENOTEMPTY", "Hook timed out"
- Symptoms: "flaky", "hanging", "zombie"
- Synonyms: "timeout/hang/freeze", "cleanup/teardown"
- Tool names, library names, file types

## When NOT to Create a Skill

- **One-off solutions** — not reusable across projects
- **Project-specific conventions** — belong in that project's CLAUDE.md
- **Standard practices** — well-documented elsewhere, Claude already knows them
- **Mechanical constraints** — enforceable by automation (hooks, linters, CI). Save skills for judgment calls.

## Common Mistakes

| Mistake | Why it's bad | Fix |
|---------|-------------|-----|
| Description summarizes workflow | Agents follow the description instead of reading the skill body | Describe only triggering conditions |
| Vague name ("helper", "utils") | Poor discoverability | Use specific gerund form |
| Over-explaining known concepts | Wastes context window tokens | Delete anything Claude already knows |
| Missing keyword coverage | Skill won't be found when needed | Add error messages, symptoms, synonyms |
| SKILL.md over 500 lines | Floods context, competes with conversation | Split heavy reference to supporting files |
