# Profile V5 — security and maintenance checks

Updated: 2026-10-11. This replaces obsolete pre-publication instructions.

## Confirmed on GitHub before this correction

- [x] Repository public; protected default branch `main`.
- [x] Ruleset ID `24860793`: required Pull Request, no branch deletion or force pushes, no bypass actors, all four mandatory checks.
- [x] Mandatory: `Offline profile integrity`, `Full-history secret scan (Gitleaks)`, `Analyze (python)`, `Analyze (actions)`.
- [x] Main CI runs `38115444615` and `38115444625` successful (79 Python tests); live refresh run `38115444638` successful.
- [x] Full-history Gitleaks step reported 97 reachable commits and 82 scanned commits, no matching leaks. The earlier incremental scan checked zero commits and is *not* the full-history result.
- [x] External GitHub Actions pinned to immutable full commit SHAs.
- [x] Hourly best-effort profile-data refresh configured; merges to relevant `main` files trigger the workflow.
- [x] Generated `profile-live` data branch is separate from protected `main`.

## Current correction: final-artifact consistency

- [ ] Merge consistency correction after all four required checks pass on the exact PR head.
- [ ] Observe successful automatic post-merge refresh.
- [ ] Verify `portfolio.json`, `portfolio.md` and SVGs agree on **the same dated data**, including when unchanged data are restored.
- [ ] Observe a successful event=`schedule` invocation; event=`push` success alone does not prove cron delivery.
- [ ] Keep README visual identity, logo, social platform icons and selected project order unchanged.

## Owner-only verification

- [ ] Review GitHub Security alerts (including dismissed), Dependabot, Secret Scanning, and push protection settings. These settings could not be read through available API access.
- [ ] Review collaborators, installed integrations, Actions default permissions and account MFA.
- [ ] Consider strict up-to-date required status checks; currently `strict_required_status_checks_policy=false`.
- [ ] `profile-live` remains unprotected to enable bot publishing. Test any proposed branch protection against this requirement.
- [ ] Visually review the profile on desktop/mobile and dark/light themes.
- [ ] Before Windows sync, inspect existing clone, local changes and commit divergence. Never use destructive reset.

Historical mobile PNG verification uses a separate read-only default workflow. It does not prevent V5 live data from refreshing.
