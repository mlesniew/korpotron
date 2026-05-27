# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## Verify Docker build before committing code or dependency changes

- **Context**: Any code or dependency changes
- **Problem**: Docker build fails
- **Rule**: After finishing implementation and before committing changes, check if docker build succeeds.
- **Applies to**: plan, implement, impl-review
