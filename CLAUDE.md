# CLAUDE.md — outdoor-data-validator

---

<!-- bmad-project-config -->
## Workflow Commands

Workflow files are located in the `workflow/` directory, to be executed step-by-step by AI Agents.

### dev-story — Develop a Story

**Trigger**: User says `start story` followed by a Story number (e.g. `1-2`)

Execution: Read `workflow/story-dev-workflow-single-repo.md` and follow the workflow steps.

**Cross-session handoff**: If a previous session only completed "Create Story" or only "Implementation", the user can use the same trigger phrase in a new session, attaching in the same message: **`BACKEND_ROOT_ABS`** (required), `BACKEND_ROOT` (optional relative path), `BRANCH`, which step was reached, and whether to continue with implementation or code review only. See the "Cross-session startup phrases" section in the workflow file.


## Project Standards

- Coding standards: refer to project-specific documentation (e.g. `docs/CODE_STYLE.md` or equivalent)
- Before making changes, read relevant existing code to understand patterns and conventions
<!-- /bmad-project-config -->
