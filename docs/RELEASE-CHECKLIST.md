# Publication gate — security hardening (2026-10-10)

## Verified project evidence
- [x] Profile refresh #7 previously passed 47 regression tests and produced validated PNG/SVG artwork.
- [x] Full current textual commit-diff inspection found no confirmed credential leakage from recognizable patterns (not exhaustive).
- [x] New security CI is configured to run full-history Gitleaks and local integrity checks.
- [x] Legacy independently writable stats and Tech Stack workflows removed on hardening branch.
- [x] Scheduled publishing now requires explicit ENABLE_SCHEDULED_PROFILE_PUBLISH=true; manual publish remains opt-in.

## Not verified / blocking Public
- [ ] Confirm full-history Gitleaks job passes on this hardening PR. Investigate alerts privately.
- [ ] Confirm offline tests, PNG verification and all relevant CI jobs pass after merging.
- [ ] Confirm whether private contribution counts appear in snapshots; choose whether daily activity may be disclosed.
- [ ] Confirm that the entire history, including binary assets and former revisions, is acceptable to publish.
- [ ] Verify logo provenance, ownership, and distinct code-vs-brand reuse rights.
- [ ] Check social links and their ownership, privacy and redirects.
- [ ] Test GitHub Mobile Android images and GitHub web Light/Dark mode.
- [ ] Review repo Security & Analysis settings, current collaborators, Actions permission defaults and Private Forks.
- [ ] Configure a branch rule that prevents force push/deletion and requires security checks for human source changes while permitting planned generated-asset updates.
- [ ] Explicitly approve changing repository visibility to Public. **Do not auto-publish.**

## Procedure
1. Review the security Pull Request, its diff and the Gitleaks report/status.
2. Merge only after checks pass; synchronize Windows working copy with `git pull --ff-only origin main`.
3. Run `py -3 -m unittest discover -s tests -v`, `py -3 scripts/validate.py` and `py -3 scripts/mobile_png.py --verify`.
4. Optionally run `profile-refresh.yml` with `publish=false`; for an explicitly approved update, use `publish=true`.
5. Keep scheduled publishing disabled until the contribution-data visibility decision.
6. Reassess the Public release gate separately. No repo visibility changes are authorized by this checklist.

Security note: `data/contributions.json` contains day-by-day activity; deleting it later will not erase previous Git history.
