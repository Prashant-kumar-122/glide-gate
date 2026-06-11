# GlideGate / CADF

See `docs/planning/cadf-framework-plan.md` for the full framework conversion plan,
current phase status, and session-by-session execution instructions.

Start every session by reading that file.

## Session workflow conventions

- **Single implementation branch.** All CADF phase work is committed to `feat/cadf-framework`.
  Never commit phase work directly to `main`. Do not create per-phase branches.
- **Always on `feat/cadf-framework`.** At the start of every session, check out
  `feat/cadf-framework` if not already on it — do not assume `main`.
- **Confirm before committing.** After finishing an implementation, show the user a concise
  summary of what changed and wait for explicit confirmation ("go ahead", "looks good", etc.)
  before running `git add` / `git commit`.
