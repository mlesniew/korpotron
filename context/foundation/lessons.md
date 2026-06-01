# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## Verify Docker build before committing code or dependency changes

- **Context**: Any code or dependency changes
- **Problem**: Docker build fails
- **Rule**: After finishing implementation and before committing changes, check if docker build succeeds.
- **Applies to**: plan, implement, impl-review

## Sync GitHub issues with context changes

- **Context**: The rule is about syncing progress with GitHub issues.
- **Problem**: The GitHub Issues are out of sync with the repository.
- **Rule**: After making new changes that result in updates to @context/foundation/changes, GitHub issues should be updated accordingly (created, commented or closed).
- **Applies to**: 10x-new, 10x-plan, 10x-plan-review, 10x-implement, 10x-impl-review
