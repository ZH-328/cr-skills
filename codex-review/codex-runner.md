# Codex Review Runner Reference

## Purpose

Command selection reference for the `codex-review` skill. Use this file when choosing the lint and `codex review` command for a repository.

## Inputs

1. **Lint command**: Auto-selected based on project type (Go, Node, Python, etc.)
2. **Review mode**: `--uncommitted` or `--commit HEAD` or `--base <branch>`
3. **Difficulty config**: `--config model_reasoning_effort=high|xhigh`
4. **Timeout guidance**: 30 minutes for difficult tasks, 10 minutes for normal tasks

## Command Examples

```bash
# Go project - Normal task
go fmt ./... && go vet ./... && codex review --uncommitted --config model_reasoning_effort=high

# Go project - Difficult task (deep reasoning)
go fmt ./... && go vet ./... && codex review --uncommitted --config model_reasoning_effort=xhigh

# Node project
npm run lint:fix && codex review --uncommitted --config model_reasoning_effort=high

# Python project
black . && ruff check --fix . && codex review --uncommitted --config model_reasoning_effort=high

# Clean working directory - Review latest commit
codex review --commit HEAD --config model_reasoning_effort=high

# Review changes relative to main branch
codex review --base main --config model_reasoning_effort=high
```

## Execution Flow

1. **Lint First**: Execute static analysis tools to fix or detect formatting issues first.
2. **Codex Review**: Then execute the selected `codex review` command.
3. **Aegis JSON**: Write review JSON to `.tmp/code-review/code-review-<月日时分>.json`.

## Output Format

Keep the complete command output available to the caller, including:

- Lint tool fix results
- Code review summary
- List of issues found
- Improvement suggestions

## Important Notes

- Must be executed in git repository directory
- Ensure codex command is properly configured and logged in
- Use the timeout guidance selected by `codex-review`
- Commands connected with `&&` stop when lint fails; report the lint failure instead of continuing silently
