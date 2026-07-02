# Codex Review Runner Reference

## Purpose

Command selection reference for the `codex-review` skill. Use this file to choose the review mode, reasoning effort, and timeout.

## Inputs

1. **Review mode**: `--uncommitted`, `--commit HEAD`, or `--base <branch>`.
2. **Difficulty config**: `--config model_reasoning_effort=high|xhigh`.
3. **Timeout guidance**: 10 minutes for normal tasks, 30 minutes for difficult tasks.

## Command Template

Use the same command shape for every project type:

```bash
codex review <review-mode> --config model_reasoning_effort=<high|xhigh>
```

Project type does not change the command. Do not run formatters, linters, or fixers as part of this runner.

## Common Commands

### Uncommitted Changes

Normal task, timeout 600000:

```bash
codex review --uncommitted --config model_reasoning_effort=high
```

Difficult task, timeout 1800000:

```bash
codex review --uncommitted --config model_reasoning_effort=xhigh
```

### Clean Working Tree

Review latest commit, timeout 600000:

```bash
codex review --commit HEAD --config model_reasoning_effort=high
```

Review latest commit, timeout 1800000:

```bash
codex review --commit HEAD --config model_reasoning_effort=xhigh
```

### Explicit Base Review

Review changes relative to `main`, timeout 600000:

```bash
codex review --base main --config model_reasoning_effort=high
```

Review changes relative to `main`, timeout 1200000:

```bash
codex review --base main --config model_reasoning_effort=xhigh
```

## Execution Notes

- Run commands from the repository root.
- Ensure `codex` is configured and logged in.
- Keep complete command output available for the final review summary and JSON conversion.
- Write the review JSON to `.tmp/code-review/code-review-<月日时分>.json` after the review completes.
