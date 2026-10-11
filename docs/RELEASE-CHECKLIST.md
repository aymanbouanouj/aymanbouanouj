# Current security verification and release checklist

Last updated: **2026-10-11**, after public release and PR #8.

**Current V4 audit addendum:** `main` is public, CodeQL checks are now required, PR #16 has merged, and the successful PR #14 proved the manual bot-review workflow. Earlier checklist entries are historical and may be superseded by the addendum below.

## Verified from GitHub

- [x] Repository `aymanbouanouj/aymanbouanouj` is **Public**.
- [x] PR #7 merged: generated evidence updates now use review-branch PRs,
  not a direct push to `main`.
- [x] PR #8 merged: CodeQL workflow added for Python and GitHub Actions.
- [x] Active Ruleset 24860793 targets the default branch (`main`).
- [x] Rule blocks deletion and non-fast-forward/force pushes.
- [x] Rule requires PRs and both `Offline profile integrity` and
  `Full-history secret scan (Gitleaks)`.
- [x] No ruleset bypass actors and no required CODEOWNERS review.
- [x] Main security run 38103231730 passed: 53 Python unit tests,
  privacy audit of 59 tracked files, validated SVG/PNG outputs, and
  a Gitleaks scan of 43 reachable commits with no detected leaks.
- [x] CodeQL run 38103231725 passed for Actions and Python.
- [x] GitHub Actions references in CodeQL workflow pinned to full SHAs
  as proposed in this hardening change.
- [x] PR #9 hardening merged and checks passed; the latest released main commit is `b5515315` before any newer PR is merged.

## Next checks requiring GitHub Settings / account access

- [ ] Review code scanning alerts, including any dismissed findings;
  successful scan jobs are not proof of zero alerts.
- [ ] Inspect Dependabot alerts, security updates, dependency graph and
  secret scanning/push protection settings. Their latest configuration
  is **not verified** by the available connector.
- [ ] Review collaborators, GitHub Apps, Actions default permissions and
  the `ENABLE_SCHEDULED_PROFILE_PUBLISH` Actions variable.
- [ ] Use a manual `publish=false` refresh dry run, then optionally
  test `publish=true` with owner approval. An actual automated PR
  publishing round trip has **not** been confirmed.
- [ ] On bot-created PRs, manually dispatch security-ci.yml and
  codeql.yml on their exact source branch and check both results.
- [ ] Only after that test, consider requiring `Analyze (actions)`
  and `Analyze (python)` as Ruleset status checks.
- [ ] Verify social links and mobile GitHub Light/Dark rendering.
- [ ] Review public contribution-calendar privacy and earlier binary
  blobs/history before claiming complete disclosure review.
- [ ] Keep ownership evidence and registration questions separate from
  code-access controls. Public repositories cannot prohibit downloads.

## Non-goals and incident response

- No procedure here claims immunity to copying or data extraction.
- No automatic merge, bypass actor or permanent PAT is introduced.
- If a secret is discovered, revoke/rotate it immediately; investigate
  prior Git history and caches before public incident closure.

## Dependency-maintenance hardening (pending review)

- [ ] Review/merge the PR introducing weekly, **non-auto-merging** Dependabot
  updates for pinned GitHub Actions and `requirements-ci.txt` (CairoSVG).
- [ ] Confirm CodeQL succeeds with its reduced permissions and non-persisted
  checkout credentials.
- [ ] Confirm Dependabot repository settings are enabled for alerts and
  vulnerability updates. The declarative config alone cannot enable them.


## V4 live public activity release gates

- [ ] Merge V4 PR only after offline integrity, Gitleaks, CodeQL Actions,
  and CodeQL Python pass against the exact PR head.
- [ ] Verify initial \`profile-live\` branch has only vetted generated artwork,
  and run the new profile-live workflow once on main after the merge.
- [ ] Check the live branch's SVG/JSON commit and the profile image render
  from a logged-out browser in dark/light themes and GitHub mobile.
- [ ] Confirm scheduled workflow runs and does not create commits if substantive
  public GitHub activity has not changed.
- [ ] Confirm public new project/commit causes the next scheduled scan to
  update the branch (subject to GitHub event and image caches).
- [ ] Keep branch Ruleset on main unchanged and no broad auto-merge.
