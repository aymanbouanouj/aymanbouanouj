# Acceptance checklist — v3.2

- [x] Read-only GitHub Actions execution succeeded on the owner's account (run 38088752616).
- [ ] GitHub GraphQL contribution totals are reviewed against the visible GitHub profile; investigate any private-contribution differences.
- [x] First combined publish job succeeded in run 38088752616; scheduled execution still needs observing.
- [ ] Check timestamp in stats.svg matches last successful sync (UTC).
- [ ] Verify the rendered profile on GitHub in dark and light modes and on a phone-width viewport.
- [ ] Verify reduced-motion presentation and readable alt text.
- [ ] Inspect all project descriptions, CI links and demo disclosures.
- [ ] Review SVG license / AB brand ownership separately from optional reusable code licensing.
- [ ] Only after the above, evaluate adding a daily schedule.

## Evidence

- Morocco2030: public Laravel project, own CI workflow, independent academic scope.
- PC-Full-Check: public PowerShell diagnostic scripts, read-only execution mode.
- VioletGate: public demo, not an authentication backend, own quality workflow.
- Ayman Calc: publicly accessible JavaScript calculator and GitHub Pages demo.

There is no claim of a live API success or full GitHub compatibility until observed.

- [ ] Verify logo in Dark/Light and project sections and badge links on mobile-width GitHub.

- [ ] Verify LinkedIn, Instagram, Facebook, X and Medium links in a browser before going public.

## Final acceptance (combined refresh)

- [ ] New engineering evidence appears after first verified Workflow run.
- [ ] Check combined workflow read-only run then scheduled/publish result and detect any API failures.
- [ ] Validate display on mobile and light mode inside real GitHub UI.
- [ ] Check social accounts resolve to accounts you control and do not expose private data.
- [ ] Review all repository files and full commit history before changing visibility.

- [x] Checked all 12 commit diffs for common token/private-key patterns; no matches found (not a comprehensive secrets audit).
- [ ] Independently verify the narrow-layout README in GitHub's renderer on an actual phone.
- [ ] Verify all social profiles belong to the owner; do not infer ownership from matching names.
