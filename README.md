# chamuka-skills

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A Claude Code plugin of reusable agent skills — techniques, patterns, and reference guides.

## Install

```
claude plugin add chamuka-inc/chamuka-skills
```

## Skills

Skills live in `skills/<skill-name>/`. Each skill contains a `SKILL.md` with YAML frontmatter and markdown instructions, conforming to the [Agent Skills specification](https://agentskills.io/specification).

- **bootstrapping-projects** — scaffold a working project from a natural-language description via a four-stage pipeline

## Authoring

See [CLAUDE.md](CLAUDE.md) for the complete skill authoring reference — frontmatter format, writing principles, common mistakes, and when (not) to create a skill.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
