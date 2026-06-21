# Repository Agent Instructions

## Required project context

Before inspecting, planning, editing, testing, committing, or reporting:

1. Read `docs/PROJECT_LOG.md` completely.
2. Read the active specification and implementation plan linked from the log.
3. Check the current Git branch and working tree; preserve user and other Agent changes.

## Required log update

Before ending every project-related conversation, update `docs/PROJECT_LOG.md`.

- Record the user's goal, checks or changes, verification evidence, remaining work, and next action.
- If no code changed, explicitly record `无代码改动` and retain the investigation or decision.
- Update current status and dated history whenever state changes.
- Use Asia/Hong_Kong date and time.
- Never mark planned or unverified work as completed.

## Confidentiality

Never record passwords, API keys, session tokens, cookies, real email addresses, `.env` contents, private photos, database records, or visual-feature cache contents. Record only a secret's purpose, storage location, and required protection.

## Handoff quality

- Keep `docs/PROJECT_LOG.md` as the only canonical status document.
- Preserve important decisions and append session records in reverse chronological order.
- Link relevant files, commits, specs, plans, and test commands.
- Preserve existing untracked runtime files and user data unless the user explicitly asks to change them.
