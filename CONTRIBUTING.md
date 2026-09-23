# Local development

This checkout is for personal modifications and migration from the sibling
`Hbm-s-Nuclear-Tech-GIT` repository. Open the shared `HBM Code` workspace and
follow `../AGENTS.md` and its workspace-local routing skill.

Keep local changes and reports here. There is no upstream contribution or
review process for this working copy; do not open issues or pull requests,
contact upstream maintainers, or publish builds unless the user requests it.
Upstream contribution policies apply only to a separately authorized upstream
submission. They do not prohibit local AI-assisted development.

- Keep each change focused. Preserve unrelated edits, useful comments, licenses,
  and original authorship; avoid unrelated changelog edits and refactoring.
- Reuse existing utilities and dependencies; avoid duplicate helpers, unused
  imports, and unfinished features. Use the project's `I18nUtil` for localization.
- For a port, compare the actual legacy behavior with the existing NEO
  implementation, including registration, resources, networking, and saved data.
- Choose checks proportional to the changed behavior. Client-only success does
  not prove dedicated-server compatibility; compatibility changes need evidence
  for the affected dependency-present and dependency-absent cases.
- Keep investigation static. Run implementation checks only within the user's
  execution and permission limits, and report exactly what was verified.
