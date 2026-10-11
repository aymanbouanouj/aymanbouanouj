# Publication gate — security hardening (2026-10-10)

## Verified project evidence
- [x] Profile refresh #7 previously passed 47 regression tests and produced validated PNG/SVG artwork.
- [x] Full current textual commit-diff inspection found no confirmed credential leakage from recognizable patterns (not exhaustive).
- [x] New security CI is configured to run full-history Gitleaks and local integrity checks.
- [x] Legacy independently writable stats and Tech Stack workflows removed on hardening branch.
- [x] Scheduled publishing now requires explicit ENABLE_SCHEDULED_PROFILE_PUBLISH=true; manual publish remains opt-in.

## Not verified / blocking Public
- [x] Full-history Gitleaks passed on the security PR and on main (run 38096332446). No findings were reported by that scanner.
- [x] Offline integrity and Gitleaks checks passed on main (run 38096332446); local user reports SVG and PNG verification passed.
- [x] Owner approves publishing GitHub contribution-calendar counts, including private aggregate counts if returned. This does not authorize making the repository Public.
- [ ] Confirm that the entire history, including binary assets and former revisions, is acceptable to publish.
- [ ] Verify logo provenance, ownership, and distinct code-vs-brand reuse rights.
- [ ] Check social links and their ownership, privacy and redirects.
- [ ] Test GitHub Mobile Android images and GitHub web Light/Dark mode.
- [ ] Review repo Security & Analysis settings, current collaborators, Actions permission defaults and Private Forks.
- [ ] Enable real branch protection / ruleset on `main`: block force pushes and deletion; require reviews and appropriate checks if compatible with verified generated updates. Currently unavailable through the connector; the private-repo Rulesets API reported a Pro-or-Public limitation.
- [ ] Explicitly approve changing repository visibility to Public. **Do not auto-publish.**

## Procedure
1. Review the security Pull Request, its diff and the Gitleaks report/status.
2. Merge only after checks pass; synchronize Windows working copy with `git pull --ff-only origin main`.
3. Run `py -3 -m unittest discover -s tests -v`, `py -3 scripts/validate.py` and `py -3 scripts/mobile_png.py --verify`.
4. Optionally run `profile-refresh.yml` with `publish=false`; for an explicitly approved update, use `publish=true`.
5. Contribution disclosure is approved; keep unattended scheduled writes disabled unless explicitly enabled through the repository variable after reviewing the publishing policy.
6. Reassess the Public release gate separately. No repo visibility changes are authorized by this checklist.

Security note: `data/contributions.json` contains day-by-day activity; deleting it later will not erase previous Git history.

## Current evidence and limitations

- [x] Verified 2026-10-10: repository is Private, `main` at `71fd10b` before this documentation update, and the security run passed.
- [x] GitHub contribution data is from the official calendar API and can contain daily private-aggregate activity.
- [ ] Verify the actual five social profiles in a logged-in browser; direct fetches were not available from the automated reviewer.
- [ ] Review collaborators, Private Forking, Actions defaults, dependency/secret scanning settings and branch rule availability in GitHub Settings. GitHub API did not expose these settings through the connected app.
- [ ] Verify real Android/web renderer appearance following the current PNG rollout.
- [ ] Obtain an **additional, explicit, separate approval** before changing visibility to Public.

## English / Français profile acceptance

- [x] README text includes professional introductions and project descriptions in English and French without changing verified PNG assets or GitHub evidence.
- [x] Publishing workflow is restricted to `refs/heads/main` and enforces the same constraint before Git push.
- [ ] Verify French accents, layout and readable wrapping on GitHub Mobile and desktop, in Dark and Light themes.
- [ ] Activate platform-level main branch protection once permitted; workflow guards alone do not protect the branch from user pushes.

- [x] Manual profile publication is guarded by owner actor and a second shell assertion. This is not an access-control substitute for GitHub repository rules.
- [ ] After making the repository public, create and activate a `main` ruleset; do not claim branch protection until GitHub confirms it is enforced.

## PR-only update migration (proposed)
- [ ] Merge the reviewed PR that changes publication from direct push to review branches.
- [ ] In Actions → General, enable GitHub Actions to create PRs only if the owner accepts automated PR proposals; no automatic merges.
- [ ] Verify a manual dry run (`publish=false`), then review a proposed update PR; approve workflow execution when required.
- [ ] Activate "Require a pull request before merging" on the main ruleset, with no bypass actors; use 0 approving reviews when working as a sole developer and require successful security checks.
- [ ] Recheck that `main` is no longer directly writable and automated status updates use a PR.
