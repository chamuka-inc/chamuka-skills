#!/usr/bin/env python3
"""
Verification harness for the project-bootstrapper skill.

Detects the stack from the project's manifest, runs install/typecheck/
lint/build/test in order, and emits a structured JSON failure report
on stdout.

Usage:
    harness.py <project-root> [--skip-tests] [--timeout-per-check 120]

Exits 0 if all checks pass, 1 if any check fails, 2 on harness error.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class Failure:
    file: str | None = None
    line: int | None = None
    column: int | None = None
    code: str | None = None
    message: str = ""
    context: str | None = None


@dataclass
class CheckResult:
    name: str
    command: str
    status: str  # pass | fail | skipped | error
    duration_ms: int = 0
    failures: list[Failure] = field(default_factory=list)
    reason: str | None = None


# --- Stack detection ----------------------------------------------------

def detect_stack(root: Path) -> str:
    if (root / "package.json").exists():
        if (root / "tsconfig.json").exists():
            return "typescript-node"
        return "javascript-node"
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return "python"
    if (root / "Cargo.toml").exists():
        return "rust"
    if (root / "go.mod").exists():
        return "go"
    return "unknown"


# --- Per-stack command tables ------------------------------------------

def commands_for(stack: str) -> list[tuple[str, str]]:
    if stack == "typescript-node":
        return [
            ("install", "npm install --no-audit --no-fund"),
            ("typecheck", "npm run typecheck --if-present"),
            ("lint", "npm run lint --if-present"),
            ("build", "npm run build --if-present"),
            ("test", "npm test --if-present"),
        ]
    if stack == "javascript-node":
        return [
            ("install", "npm install --no-audit --no-fund"),
            ("lint", "npm run lint --if-present"),
            ("build", "npm run build --if-present"),
            ("test", "npm test --if-present"),
        ]
    if stack == "python":
        has_uv = shutil.which("uv") is not None
        if has_uv:
            return [
                ("install", "uv sync"),
                ("typecheck", "uv run mypy ."),
                ("lint", "uv run ruff check ."),
                ("test", "uv run pytest"),
            ]
        return [
            ("install", "python3 -m venv .venv && .venv/bin/pip install -e ."),
            ("typecheck", ".venv/bin/mypy ."),
            ("lint", ".venv/bin/ruff check ."),
            ("test", ".venv/bin/pytest"),
        ]
    if stack == "rust":
        return [
            ("build", "cargo check --all-targets"),
            ("lint", "cargo clippy --all-targets -- -D warnings"),
            ("test", "cargo test"),
        ]
    if stack == "go":
        return [
            ("install", "go mod download"),
            ("build", "go build ./..."),
            ("test", "go test ./..."),
        ]
    return []


# --- Output parsers ----------------------------------------------------

TS_ERROR_RE = re.compile(
    r"^(?P<file>[^(]+)\((?P<line>\d+),(?P<col>\d+)\):\s+error\s+(?P<code>TS\d+):\s+(?P<msg>.*)$"
)


def parse_typescript(output: str) -> list[Failure]:
    failures = []
    for line in output.splitlines():
        m = TS_ERROR_RE.match(line.strip())
        if m:
            failures.append(Failure(
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")),
                code=m.group("code"),
                message=m.group("msg"),
            ))
    return failures


MYPY_ERROR_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)?\s+error:\s+(?P<msg>.*?)(?:\s+\[(?P<code>[^\]]+)\])?$"
)


def parse_mypy(output: str) -> list[Failure]:
    failures = []
    for line in output.splitlines():
        m = MYPY_ERROR_RE.match(line.strip())
        if m:
            failures.append(Failure(
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")) if m.group("col") else None,
                code=m.group("code"),
                message=m.group("msg"),
            ))
    return failures


CARGO_ERROR_RE = re.compile(r"^error(?:\[(?P<code>E\d+)\])?:\s+(?P<msg>.*)$")
CARGO_LOC_RE = re.compile(r"^\s*-->\s+(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+)$")


def parse_cargo(output: str) -> list[Failure]:
    failures = []
    lines = output.splitlines()
    i = 0
    while i < len(lines):
        m = CARGO_ERROR_RE.match(lines[i].strip())
        if m:
            file, line_no, col = None, None, None
            for j in range(i + 1, min(i + 5, len(lines))):
                lm = CARGO_LOC_RE.match(lines[j])
                if lm:
                    file = lm.group("file")
                    line_no = int(lm.group("line"))
                    col = int(lm.group("col"))
                    break
            failures.append(Failure(
                file=file, line=line_no, column=col,
                code=m.group("code"), message=m.group("msg"),
            ))
        i += 1
    return failures


ESLINT_RE = re.compile(
    r"^\s+(?P<line>\d+):(?P<col>\d+)\s+(?:error|warning)\s+(?P<msg>.+?)\s+(?P<code>\S+)$"
)
ESLINT_FILE_RE = re.compile(r"^(/[^\s]+|[A-Z]:\\[^\s]+)$")


def parse_eslint(output: str) -> list[Failure]:
    failures = []
    current_file = None
    for line in output.splitlines():
        fm = ESLINT_FILE_RE.match(line.strip())
        if fm:
            current_file = fm.group(0)
            continue
        m = ESLINT_RE.match(line)
        if m and current_file:
            failures.append(Failure(
                file=current_file,
                line=int(m.group("line")),
                column=int(m.group("col")),
                code=m.group("code"),
                message=m.group("msg"),
            ))
    return failures


RUFF_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>[A-Z]+\d+)\s+(?P<msg>.*)$"
)


def parse_ruff(output: str) -> list[Failure]:
    failures = []
    for line in output.splitlines():
        m = RUFF_RE.match(line.strip())
        if m:
            failures.append(Failure(
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")),
                code=m.group("code"),
                message=m.group("msg"),
            ))
    return failures


def parse_generic(output: str, check_name: str) -> list[Failure]:
    """Fallback: dump the last ~50 lines as a single failure."""
    tail = "\n".join(output.splitlines()[-50:])
    return [Failure(
        message=f"{check_name} failed; tail of output:\n{tail}",
    )]


def select_parser(check_name: str, command: str):
    if check_name == "typecheck" and ("tsc" in command or "npm" in command):
        return parse_typescript
    if check_name == "typecheck" and "mypy" in command:
        return parse_mypy
    if check_name == "lint" and ("eslint" in command or "npm" in command):
        return parse_eslint
    if check_name == "lint" and "ruff" in command:
        return parse_ruff
    if "cargo" in command:
        return parse_cargo
    return lambda out: parse_generic(out, check_name)


# --- Failure clustering ------------------------------------------------

def deduplicate(failures: list[Failure]) -> list[Failure]:
    """Group by (code, message-fingerprint). Keep first occurrence,
    annotate count if duplicates exist."""
    seen: dict[tuple, dict] = {}
    for f in failures:
        key = (f.code, f.message[:80])
        if key in seen:
            seen[key]["count"] += 1
        else:
            seen[key] = {"failure": f, "count": 1}

    result = []
    for entry in seen.values():
        f = entry["failure"]
        if entry["count"] > 1:
            f.message = f"{f.message}  [×{entry['count']} occurrences]"
        result.append(f)
    return result


# --- npm --if-present detection ----------------------------------------

def npm_script_exists(name: str, command: str, root: Path) -> bool | None:
    """Return False if this is an npm --if-present command for a missing script.
    Return None for non-npm commands (caller should run normally)."""
    if "--if-present" not in command or "npm" not in command:
        return None
    pkg = root / "package.json"
    if not pkg.exists():
        return None
    try:
        data = json.loads(pkg.read_text())
        scripts = data.get("scripts", {})
        # extract script name: "npm run lint --if-present" -> "lint", "npm test --if-present" -> "test"
        parts = command.split()
        if "test" in parts:
            return "test" in scripts
        for i, p in enumerate(parts):
            if p == "run" and i + 1 < len(parts):
                return parts[i + 1] in scripts
    except (json.JSONDecodeError, KeyError):
        pass
    return None


# --- Runner ------------------------------------------------------------

def run_check(name: str, command: str, root: Path, timeout: int) -> CheckResult:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name, command=command, status="error",
            duration_ms=int((time.monotonic() - start) * 1000),
            reason=f"timed out after {timeout}s",
        )
    except FileNotFoundError as e:
        return CheckResult(
            name=name, command=command, status="error",
            duration_ms=int((time.monotonic() - start) * 1000),
            reason=f"command not found: {e}",
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    if proc.returncode == 0:
        return CheckResult(name=name, command=command, status="pass",
                           duration_ms=duration_ms)

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    parser = select_parser(name, command)
    failures = parser(combined)
    return CheckResult(
        name=name, command=command, status="fail",
        duration_ms=duration_ms,
        failures=deduplicate(failures),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--timeout-per-check", type=int, default=120)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}), file=sys.stderr)
        return 2

    stack = detect_stack(root)
    if stack == "unknown":
        print(json.dumps({
            "stack": "unknown",
            "checks": [],
            "all_passed": True,
            "reason": "no recognized manifest",
        }, indent=2))
        return 0

    checks = commands_for(stack)
    results: list[CheckResult] = []
    upstream_failed = False

    for name, command in checks:
        if upstream_failed:
            results.append(CheckResult(
                name=name, command=command, status="skipped",
                reason="blocked by upstream failure",
            ))
            continue
        if args.skip_tests and name == "test":
            results.append(CheckResult(
                name=name, command=command, status="skipped",
                reason="--skip-tests set",
            ))
            continue

        has_script = npm_script_exists(name, command, root)
        if has_script is False:
            results.append(CheckResult(
                name=name, command=command, status="skipped",
                reason=f"no '{name}' script in package.json",
            ))
            continue

        result = run_check(name, command, root, args.timeout_per_check)
        results.append(result)
        if result.status in ("fail", "error"):
            upstream_failed = True

    report = {
        "stack": stack,
        "checks": [_clean(r) for r in results],
        "all_passed": not upstream_failed,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if not upstream_failed else 1


def _clean(r: CheckResult) -> dict:
    d = asdict(r)
    if not d.get("failures"):
        d.pop("failures", None)
    if d.get("reason") is None:
        d.pop("reason", None)
    return d


if __name__ == "__main__":
    sys.exit(main())
