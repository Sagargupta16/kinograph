## Summary

<!-- 1-3 sentences: what this PR changes and why. -->

## Change type

- [ ] New or changed style
- [ ] Engine drawing or sound
- [ ] Gate (Q code) or its fixture
- [ ] Skill, agent or reference content
- [ ] Bug fix
- [ ] Docs / CI / tooling

## Checklist

- [ ] `python scripts/check.py` passes
- [ ] `ruff check` and `ruff format --check` pass on `skills/praxinoscope/engine` and `scripts`
- [ ] `npx -y @sagargupta1610/skillcheck@0.2.5 lint skills` reports no errors
- [ ] `qa.py selftest` from a copy of the engine ends `SELFTEST: PASS`
- [ ] A drawing, sound or gate change: the template renders at 1920x1080 and 1080x1920 with `PROOF: PASS`, a `DELIVERED` line and `QA: PASS` (paste them)
- [ ] CHANGELOG.md entry under a concrete version; version bumped in both `.claude-plugin/*.json` files when releasing
- [ ] Original work only, no en or em dashes, no absolute home paths, no secrets
