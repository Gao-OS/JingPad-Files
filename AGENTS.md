# Repository Guidelines

## Project Structure & Module Organization

This repository records JingPad C1/JingOS Linux development; it is not an application or a full kernel checkout.

- `README.md`: current status and reading order.
- `docs/`: device access, software management, application development, firmware links, and dated experiment logs.
- `patches/`: numbered Linux 4.14 compatibility patches (`0001-description.patch`).
- `tools/kernel/`: ARM64 syscall probes (`probe-*.py`).
- `.github/workflows/claude.yml`: comment-triggered assistant workflow, not a test pipeline.

Kernel sources, toolchains, build artifacts, and private recovery materials live outside this checkout; firmware downloads are linked through Releases.

## Build, Test, and Development Commands

Run these checks from the repository root:

```bash
git diff --check -- README.md AGENTS.md docs/ tools/ .github/
python3 -c 'import ast; from pathlib import Path; [ast.parse(p.read_text(), filename=str(p)) for p in Path("tools/kernel").glob("*.py")]'
git apply --numstat patches/0001-statx-mount-id-preserve-module-abi.patch
```

These check whitespace, parse Python without executing device syscalls, and validate patch structure. Repeat patch parsing for each changed patch. Check relative Markdown links manually. For kernel builds and patch application against pinned source, follow [the execution log](docs/kernel-backport-2026-11-18.md); there is no root build command.

## Coding Style & Naming Conventions

Write documentation in English, using relative links and dated evidence. Use four-space Python indentation and existing standard-library conventions; preserve kernel tabs and unified-diff context. Do not strip structural whitespace from patch context. No formatter or linter is configured.

## Testing Guidelines

No unit-test framework or coverage threshold is configured. Treat `probe-*.py` as ARM64 device integration checks, following the execution log's ADB commands. The bind-mount probe requires root and creates a private mount namespace. Inspect JSON for `all_verified: true`; ADB's host exit status alone is insufficient. Record kernel markers, expected failures, and untested behavior separately from passing results.

## Commit & Pull Request Guidelines

Follow recent subjects such as `docs(jingos): clarify recovery checks` and `feat(kernel): add compatibility backport`. Keep commits focused. PRs should explain purpose, relevant device/source versions, validation, and limitations; link issues and include screenshots for GUI changes.

## Device Safety & Workspace Boundaries

Keep signing keys, partition/calibration backups, firmware images, and personal logs outside Git. Device writes require authorization, verified backups, and a recovery path. Preserve vendor ABI/configuration and documented build resource limits. Work on the current branch; create branches or worktrees only when explicitly requested.
