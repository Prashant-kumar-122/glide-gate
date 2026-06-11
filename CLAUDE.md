# GlideGate / CADF

See `docs/planning/cadf-framework-plan.md` for the full framework conversion plan,
current phase status, and session-by-session execution instructions.

Start every session by reading that file.

## Session workflow conventions

- **Feature branches.** Every phase must be implemented on `feat/cadf-phase-{N}` (e.g.
  `feat/cadf-phase-0.5`). Never commit phase work directly to `main`.
- **Confirm before committing.** After finishing an implementation, show the user a concise
  summary of what changed and wait for explicit confirmation ("go ahead", "looks good", etc.)
  before running `git add` / `git commit`.
