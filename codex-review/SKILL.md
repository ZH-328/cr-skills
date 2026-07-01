---
name: codex-review
description: "Professional code review workflow for Codex. Automatically prepares code changes, runs lint and codex review, then writes local review JSON without uploading data. Triggers: code review, review, 代码审核, 代码审查, 检查代码"
metadata:
  short-description: Run Codex code review without uploading data
---

# Codex Code Review Skill

## Trigger Conditions

Triggered when user input contains:

- "代码审核", "代码审查", "审查代码", "审核代码"
- "review", "code review", "review code", "codex 审核"
- "帮我审核", "检查代码", "审一下", "看看代码"

## Core Concept: Intention vs Implementation

Running `codex review --uncommitted` alone only shows AI "what was done (Implementation)".
Recording intention first tells AI "what you wanted to do (Intention)".

**"Code changes + intention description" as combined input is the most effective way to improve AI code review quality.**

## Skill Architecture

This skill operates in three phases:

1. **Preparation Phase** (current context): Check working directory, update CHANGELOG
2. **Review Phase** (current task): Select and run lint + `codex review` commands directly
3. **Local Result Phase** (current context): Convert review output to local Aegis-compatible JSON, without invoking upload

## Execution Steps

### 0. [First] Check Working Directory Status

```bash
git diff --name-only && git status --short
```

**Decide review mode based on output:**

- **Has uncommitted changes** → Continue with steps 1-6 (normal flow)
- **Clean working directory** → Skip steps 1-2, run `codex review --commit HEAD`, then continue with steps 4-6

### 1. [Mandatory] Check if CHANGELOG is Updated

**Before any review, must check if CHANGELOG.md contains description of current changes.**

```bash
# Check if CHANGELOG.md is in uncommitted changes
git diff --name-only | grep -E "(CHANGELOG|changelog)"
```

**If CHANGELOG is not updated, you must automatically perform the following (don't ask user to do it manually):**

1. **Analyze changes**: Run `git diff --stat` and `git diff` to get complete changes
2. **Auto-generate CHANGELOG entry**: Generate compliant entry based on code changes
3. **Write to CHANGELOG.md**: Use Edit tool to insert entry at top of `[Unreleased]` section
4. **Continue review flow**: Immediately proceed to next steps after CHANGELOG update

**Auto-generated CHANGELOG entry format:**

```markdown
## [Unreleased]

### Added / Changed / Fixed

- Feature description: what problem was solved or what functionality was implemented
- Affected files: main modified files/modules
```

**Example - Auto-generation Flow:**

```
1. Detected CHANGELOG not updated
2. Run git diff --stat, found handlers/responses.go modified (+88 lines)
3. Run git diff to analyze details: added CompactHandler function
4. Auto-generate entry:
   ### Added
   - Added `/v1/responses/compact` endpoint for conversation context compression
   - Supports multi-channel failover and request body size limits
5. Use Edit tool to write to CHANGELOG.md
6. Continue with lint and codex review
```

### 2. [Critical] Stage All New Files

**Before invoking codex review, must add all new files (untracked files) to git staging area, otherwise codex will report P1 error.**

```bash
# Check for new files
git status --short | grep "^??"
```

**If there are new files, automatically execute:**

```bash
# Safely stage all new files (handles empty list and special filenames)
git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do git add -- "$f"; done
```

**Explanation:**

- `-z` uses null character to separate filenames, correctly handles filenames with spaces/newlines
- `while IFS= read -r -d ''` reads filenames one by one
- `git add -- "$f"` uses `--` separator, correctly handles filenames starting with `-`
- When no new files exist, loop body doesn't execute, safely skipped
- This won't stage modified files, only handles new files
- codex needs files to be tracked by git for proper review

### 3. Evaluate Task Difficulty and Run Codex Review

**Count change scale:**

```bash
# Count number of changed files and lines of code
git diff --stat | tail -1
```

**Difficulty Assessment Criteria:**

**Difficult Tasks** (meets any condition):

- Modified files ≥ 10
- Total code changes (insertions + deletions) ≥ 500 lines
- Single metric: insertions ≥ 300 lines OR deletions ≥ 300 lines
- Involves core architecture/algorithm changes
- Cross-module refactoring
- Config: `model_reasoning_effort=xhigh`, timeout 30 minutes

**Normal Tasks** (other cases):

- Config: `model_reasoning_effort=high`, timeout 10 minutes

**Evaluation Method:**

You MUST parse the `git diff --stat` output correctly to determine difficulty:

```bash
# Get the summary line (last line of git diff --stat)
git diff --stat | tail -1
# Example outputs:
# "20 files changed, 342 insertions(+), 985 deletions(-)"
# "1 file changed, 50 insertions(+)"  # No deletions
# "3 files changed, 120 deletions(-)"  # No insertions
```

**Parsing Rules:**
1. Extract file count from "X file(s) changed" (handle both "1 file" and "N files")
2. Extract insertions from "Y insertion(s)(+)" if present (handle both "1 insertion" and "N insertions"), otherwise 0
3. Extract deletions from "Z deletion(s)(-)" if present (handle both "1 deletion" and "N deletions"), otherwise 0
4. Calculate total changes = insertions + deletions

**Important Edge Cases:**
- Single file: `"1 file changed"` (singular form)
- No insertions: Git omits `"insertions(+)"` entirely → treat as 0
- No deletions: Git omits `"deletions(-)"` entirely → treat as 0
- Pure rename: May show `"0 insertions(+), 0 deletions(-)"` or omit both

**Decision Logic (ANY condition triggers xhigh):**
- IF file_count >= 10 → xhigh
- IF total_changes >= 500 → xhigh
- IF insertions >= 300 → xhigh
- IF deletions >= 300 → xhigh
- ELSE → high

**Example Cases:**
- ✅ "20 files changed, 342 insertions(+), 985 deletions(-)" → xhigh (files=20≥10, total=1327≥500, deletions=985≥300)
- ✅ "5 files changed, 600 insertions(+), 50 deletions(-)" → xhigh (total=650≥500, insertions=600≥300)
- ✅ "12 files changed, 100 insertions(+), 50 deletions(-)" → xhigh (files=12≥10)
- ✅ "1 file changed, 400 deletions(-)" → xhigh (deletions=400≥300)
- ❌ "3 files changed, 150 insertions(+), 80 deletions(-)" → high (all conditions fail)
- ❌ "1 file changed, 50 insertions(+)" → high (no deletions, total=50<500)

**Run the selected command directly from the repository root.**

Use the project type and difficulty assessment to choose the command. See [codex-runner.md](codex-runner.md) for the same command templates as a compact reference.

```bash
Go project - Difficult task:
  go fmt ./... && go vet ./... && codex review --uncommitted --config model_reasoning_effort=xhigh
  (timeout: 1800000)

Go project - Normal task:
  go fmt ./... && go vet ./... && codex review --uncommitted --config model_reasoning_effort=high
  (timeout: 600000)

Node project - Difficult task:
  npm run lint:fix && codex review --uncommitted --config model_reasoning_effort=xhigh
  (timeout: 1800000)

Node project - Normal task:
  npm run lint:fix && codex review --uncommitted --config model_reasoning_effort=high
  (timeout: 600000)

Python project - Difficult task:
  black . && ruff check --fix . && codex review --uncommitted --config model_reasoning_effort=xhigh
  (timeout: 1800000)

Python project - Normal task:
  black . && ruff check --fix . && codex review --uncommitted --config model_reasoning_effort=high
  (timeout: 600000)

Clean working directory:
  codex review --commit HEAD --config model_reasoning_effort=high
  (timeout: 600000)
```

### 4. Self-Correction

If Codex finds Changelog description inconsistent with code logic:

- **Code error** → Fix code
- **Description inaccurate** → Update Changelog

### 5. Generate Local Review JSON

After lint and `codex review` complete, convert the review result into the local JSON format compatible with the `upload-code-review` skill template.

**Output path:**

```bash
.tmp/code-review/code-review-<月日时分>.json
```

Create `.tmp/code-review` if it does not exist.

**Required JSON format:**

```json
{
  "review_record": {
    "score": 0
  },
  "findings": []
}
```

**Generation rules:**

1. Strictly follow `../upload-code-review/TEMPLATE.md`.
2. `review_record.score` must be an integer or float from 0 to 100.
3. If `codex review` reports no issues, still generate the JSON with `findings: []` so the local review record is complete.
4. For each issue found by `codex review`, create one `findings` item with:
   - `title`: concise issue title
   - `file`: repository-relative file path
   - `line_number_pairs`: array of `{ "start": <line>, "end": <line> }`
   - `summary`: one-sentence issue summary
   - `message`: detailed explanation of why this is a problem and the root cause
   - `suggestion`: concrete fix recommendation
   - `severity`: one of `严重`, `高`, `中`, `低`
   - `category`: one of `bug`, `建议`, `提示`
   - `matched_rule_ids`: use matching predefined rule IDs only when explicitly known; otherwise use `[]`
5. Do not invent `matched_rule_ids`. Automatically detected findings without a known predefined rule must use an empty array.

**Severity mapping guidance:**

- Critical correctness, security, data loss, or production outage risk → `严重`
- High-confidence bug or serious maintainability/performance risk → `高`
- Moderate risk or localized behavior issue → `中`
- Minor suggestion, readability issue, or low-risk cleanup → `低`

**Category mapping guidance:**

- Defect, regression, security issue, data corruption, incorrect behavior → `bug`
- Improvement that should be addressed but is not a confirmed defect → `建议`
- Informational note or optional cleanup → `提示`

### 6. Do Not Upload Review Result

After generating the JSON file, stop the code-review workflow. Do not invoke the `upload-code-review` skill, and do not run `../upload-code-review/scripts/uploader.py`.

**Upload policy:**

- Upload is disabled for every `codex-review` run.
- Keep the local review output and generated JSON file.
- Report the review result and the local JSON file path only.
- Only upload if the user explicitly requests the separate `upload-code-review` skill or directly asks to run the upload command.

## Complete Review Protocol

1. **[GATE] Check CHANGELOG** - Auto-generate and write if not updated (leverage current context to understand change intention)
2. **[PREPARE] Stage Untracked Files** - Add all new files to git staging area (avoid codex P1 error)
3. **[EXEC] Lint + codex review** - Run the selected lint and `codex review` commands directly
4. **[FIX] Self-Correction** - Fix code or update description when intention ≠ implementation
5. **[FORMAT] Generate Local Review JSON** - Convert codex review output to `upload-code-review` compatible JSON format
6. **[STOP] No upload** - Do not invoke `upload-code-review` or run `uploader.py`

## Codex Review Command Reference

### Basic Syntax

```bash
codex review [OPTIONS] [PROMPT]
```

**Note**: `[PROMPT]` parameter cannot be used with `--uncommitted`, `--base`, or `--commit`.

### Common Options

| Option                     | Description                                                      | Example                                                      |
| -------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| `--uncommitted`            | Review all uncommitted changes in working directory (staged + unstaged + untracked) | `codex review --uncommitted`                                 |
| `--base <BRANCH>`          | Review changes relative to specified base branch                 | `codex review --base main`                                   |
| `--commit <SHA>`           | Review changes introduced by specified commit                    | `codex review --commit HEAD`                                 |
| `--title <TITLE>`          | Optional commit title, displayed in review summary               | `codex review --uncommitted --title "feat: add JSON parser"` |
| `-c, --config <key=value>` | Override configuration values                                    | `codex review --uncommitted -c model="o3"`                   |

### Usage Examples

```bash
# 1. Review all uncommitted changes (most common)
codex review --uncommitted

# 2. Review latest commit
codex review --commit HEAD

# 3. Review specific commit
codex review --commit abc1234

# 4. Review all changes in current branch relative to main
codex review --base main

# 5. Review changes in current branch relative to develop
codex review --base develop

# 6. Review with title (title shown in review summary)
codex review --uncommitted --title "fix: resolve JSON parsing errors"

# 7. Review using specific model
codex review --uncommitted -c model="o3"
```

### Important Limitations

- `--uncommitted`, `--base`, `--commit` are mutually exclusive, cannot be used together
- `[PROMPT]` parameter is mutually exclusive with the above three options
- Must be executed in a git repository directory

## Important Notes

- Ensure execution in git repository directory
- **Timeout automatically adjusted based on task difficulty:**
    - Difficult tasks: 30 minutes (`timeout: 1800000`)
    - Normal tasks: 10 minutes (`timeout: 600000`)
- codex command must be properly configured and logged in
- codex automatically processes in batches for large changes
- **CHANGELOG.md must be in uncommitted changes, otherwise Codex cannot see intention description**
- **Aegis upload is disabled in `codex-review`; keep results local**
- **Do not invoke `upload-code-review` or run `uploader.py` unless the user explicitly asks for upload**

## Design Rationale

1. **CHANGELOG update needs current context**: Use the user's request and current changes to generate an accurate intention description.
2. **Codex review needs repository state**: Run `codex review` from the git repository after preparation is complete.
3. **Local JSON generation needs review output**: Convert review findings into the existing review JSON schema after the review command finishes.
4. **Upload is opt-in**: Preserve local review output and JSON; upload only when explicitly requested separately.
