---
name: codex-review
description: "Professional code review workflow for Codex. Automatically prepares code changes, runs lint and codex review, writes review JSON, and uploads it. Triggers: code review, review, 代码审核, 代码审查, 检查代码"
metadata:
  short-description: Run Codex code review and upload Aegis JSON
---

# Codex Code Review Skill

## Purpose

Run a code review workflow that combines implementation changes with a short intention record, executes lint plus `codex review`, writes an Aegis-compatible JSON result, and uploads it through `upload-code-review`.

## Execution Protocol

1. Check working directory status.
2. Ensure the review intention is recorded in `CHANGELOG.md`.
3. Stage untracked files so `codex review` can see them.
4. Select review effort from change size.
5. Run lint plus `codex review` from the repository root.
6. Fix code or CHANGELOG if review output shows an intention/implementation mismatch.
7. Generate the local review JSON.
8. Invoke `upload-code-review` to upload the generated JSON.

## 1. Check Repository State

Run:

```bash
git diff --name-only
git status --short
```

Review mode:

- If the working directory has uncommitted changes, review with `codex review --uncommitted`.
- If the working directory is clean, skip preparation and review `HEAD` with `codex review --commit HEAD`.

## 2. Record Review Intention

Before reviewing uncommitted changes, check whether `CHANGELOG.md` is part of the current diff:

```bash
git diff --name-only | grep -E "(CHANGELOG|changelog)"
```

If no changelog file is changed:

1. Inspect `git diff --stat` and `git diff`.
2. Generate a concise entry describing the intent of the current change.
3. Insert it at the top of the `[Unreleased]` section in `CHANGELOG.md`.
4. Continue the review workflow immediately.

Entry shape:

```markdown
## [Unreleased]

### Added / Changed / Fixed

- Describe the problem solved or behavior changed.
- List the main affected modules or files.
```

If no suitable `CHANGELOG.md` or `[Unreleased]` section exists, report that blocker instead of inventing a new release structure.

## 3. Stage Untracked Files

Before invoking `codex review`, stage only new untracked files:

```bash
git status --short | grep "^??"
git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do git add -- "$f"; done
```

Do not stage already-modified tracked files. This step only makes new files visible to the review command.

## 4. Select Review Effort

Use `git diff --stat | tail -1` to classify the task.

Use `model_reasoning_effort=xhigh` and a 30 minute timeout if any condition is true:

- Changed files >= 10
- Insertions + deletions >= 500
- Insertions >= 300
- Deletions >= 300
- The change is core architecture, algorithmic, or cross-module refactoring

Otherwise use `model_reasoning_effort=high` and a 10 minute timeout.

When parsing `git diff --stat`, treat omitted insertion or deletion counts as `0`, and handle both singular and plural Git wording.

## 5. Run Lint And Codex Review

Choose the command from [codex-runner.md](codex-runner.md), based on:

- Project type: Go, Node, Python, or clean working tree
- Review mode: `--uncommitted`, `--commit HEAD`, or another explicit base mode
- Review effort: `high` or `xhigh`

Run the selected command directly from the repository root. Commands joined with `&&` must stop if lint fails; report the lint failure instead of continuing silently.

## 6. Self-Correction

If review output shows the CHANGELOG intent does not match the implementation:

- Fix the code when the implementation is wrong.
- Update `CHANGELOG.md` when the description is inaccurate.

Then rerun the necessary checks before generating the JSON result.

## 7. Generate Aegis Upload JSON

After lint and `codex review` complete, create:

```bash
.tmp/code-review/code-review-<月日时分>.json
```

Create `.tmp/code-review` if needed.

The JSON must strictly follow `../upload-code-review/TEMPLATE.md`.

Rules:

- `review_record.score` must be a number from 0 to 100.
- `review_record.gitlab_url` must contain the current repository GitLab URL when it can be resolved from `git config --get remote.origin.url`; normalize SSH remotes like `git@gitlab.example.com:group/project.git` to `https://gitlab.example.com/group/project`.
- Generate the JSON even when there are no findings.
- Use `findings: []` when `codex review` reports no issues.
- Do not invent `matched_rule_ids`; use `[]` unless a predefined rule is explicitly known.

## 8. Upload Review Result

After generating the JSON file, invoke the `upload-code-review` skill to upload the review result to Aegis.

Use the generated JSON path as the upload input:

```bash
python scripts/uploader.py --file-path <代码审查数据JSON文件路径>
```

Failure policy:

- Upload is enabled by default for every successful `codex-review` run.
- If upload succeeds, report the Aegis upload summary together with the review result.
- If upload fails, keep the code review result visible to the user and report the upload failure reason.
- Do not retry unless the user explicitly asks.
