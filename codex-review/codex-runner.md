# Codex Review Runner Reference

## Purpose

Command selection reference for the `codex-review` skill. Use this file to choose the lint command, review mode, reasoning effort, and timeout.

## Inputs

1. **Project type**: Go, Node, Python, or clean working tree.
2. **Review mode**: `--uncommitted`, `--commit HEAD`, or `--base <branch>`.
3. **Difficulty config**: `--config model_reasoning_effort=high|xhigh`.
4. **Timeout guidance**: 10 minutes for normal tasks, 30 minutes for difficult tasks.

## Command Matrix

### Go

Normal task, timeout 600000:

```bash
go fmt ./... && go vet ./... && codex review --uncommitted --config model_reasoning_effort=high
```

Difficult task, timeout 1800000:

```bash
go fmt ./... && go vet ./... && codex review --uncommitted --config model_reasoning_effort=xhigh
```

### Node

Normal task, timeout 600000:

```bash
npm run lint:fix && codex review --uncommitted --config model_reasoning_effort=high
```

Difficult task, timeout 1800000:

```bash
npm run lint:fix && codex review --uncommitted --config model_reasoning_effort=xhigh
```

### Python

Normal task, timeout 600000:

```bash
black . && ruff check --fix . && codex review --uncommitted --config model_reasoning_effort=high
```

Difficult task, timeout 1800000:

```bash
black . && ruff check --fix . && codex review --uncommitted --config model_reasoning_effort=xhigh
```

### Clean Working Tree

Review latest commit, timeout 600000:

```bash
codex review --commit HEAD --config model_reasoning_effort=high
```

### Explicit Base Review

Review changes relative to `main`, timeout based on difficulty:

```bash
codex review --base main --config model_reasoning_effort=high
codex review --base main --config model_reasoning_effort=xhigh
```

## Execution Notes

- Run commands from the repository root.
- Ensure `codex` is configured and logged in.
- Commands connected with `&&` stop when lint fails; report the lint failure instead of continuing silently.
- Keep complete command output available for the final review summary and JSON conversion.
- Write the review JSON to `.tmp/code-review/code-review-<月日时分>.json` after the review completes.
