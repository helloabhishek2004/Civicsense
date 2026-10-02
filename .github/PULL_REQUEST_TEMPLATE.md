## Summary

<!-- What does this PR do? Keep it to 2–3 sentences. -->


## Type of change

- [ ] 🐛 Bug fix (non-breaking)
- [ ] ✨ New feature (non-breaking)
- [ ] 💥 Breaking change (fix or feature that changes existing behavior)
- [ ] 📝 Documentation only
- [ ] 🤖 ML / data (model, dataset, evaluation)
- [ ] ♻️ Refactoring (no behavior change)
- [ ] 🔧 Chore (build, tooling, deps, CI)

## Related issue(s)

<!-- Link to the issue this PR resolves -->
Fixes #

## Checklist

### All PRs
- [ ] Tests pass locally (`pytest` / `npm test` / `gradlew testDebugUnitTest`)
- [ ] Lint and type checks pass (`ruff check` + `mypy` / `tsc --noEmit` + `eslint`)
- [ ] No `print()`, `console.log`, or `Log.d` debug statements left in production code paths
- [ ] No secrets, credentials, API keys, or real personal data committed
- [ ] PR is focused — unrelated changes are in a separate PR

### If changing backend, API, or database
- [ ] New/changed endpoints documented in `docs/API.md`
- [ ] Database changes go through an Alembic migration (never ad-hoc)
- [ ] `Report` and `Issue` domain distinction is preserved

### If changing ML or AI pipeline
- [ ] Evaluation scripts updated and new results committed to `datasets/evaluation_runs/`
- [ ] Model changes include before/after metric comparison
- [ ] `CHANGELOG.md` entry added

### If this is a notable change
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`

## Screenshots

<!-- Add screenshots for any UI changes. Drag and drop images here. -->

## Notes for reviewers

<!-- Anything that needs extra context, design decisions, or known limitations? -->
