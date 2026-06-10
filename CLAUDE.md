# CLAUDE.md

## Branching workflow

Never commit directly to `main`. All work goes on a feature branch.

1. At the start of a session, create a branch: `git checkout -b <short-descriptive-name>`
   - Use kebab-case, e.g. `add-numeric-module`, `fix-clamp-bounds`, `docs-update`
2. Commit work to that branch as you go.
3. When the user asks to create a PR, push the branch and open one against `main` with `gh pr create`.

If a session begins and the working tree is already on `main` with uncommitted changes, move them to a new branch before committing:
```
git checkout -b <branch-name>
```
