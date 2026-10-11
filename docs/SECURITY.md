# Security policy — Ayman GitHub profile

## Current verified posture (2026-10-11)

This repository is **Public** and `main` is protected by the active
[Protect Main — Ayman Profile ruleset](https://github.com/aymanbouanouj/aymanbouanouj/rules/24860793)
(rule ID 24860793). Its verified controls are:

- Block branch deletion and force pushes (non-fast-forward updates).
- Require a Pull Request before merging into the default branch.
- Require the successful `Offline profile integrity` and
  `Full-history secret scan (Gitleaks)` checks.
- No bypass actors. Required reviewer approvals: zero;
  CODEOWNERS approval requirement: disabled for the single maintainer.

A collaborator with write permission could still open and merge a PR once
required checks pass: these controls are **not independent human approval**.
GitHub account security, installations, collaborators, alert settings, and
GitHub Actions repository variables cannot be independently verified through
the available repository connection.

## Continuous checks

- `.github/workflows/security-ci.yml`: regression checks, an explicit
  tracked-filename privacy gate, XML/SVG/PNG provenance checks, and Gitleaks
  scanning all reachable Git history. The workflow uses read-only token
  permissions and fixed action commit SHAs.
- `.github/workflows/codeql.yml`: CodeQL for Python and GitHub Actions.
  External actions are pinned to immutable full commit SHAs; it runs on
  push, PR, schedule and manual `workflow_dispatch`. A green CodeQL job
  indicates the scan completed; **review the actual code scanning alerts**.
  As of this document, CodeQL jobs have not been added to the Ruleset's
  required status checks.
- `.github/workflows/profile-refresh.yml`: read-only verification by
  default. Publishing is manually owner-triggered or requires the explicitly
  opted-in `ENABLE_SCHEDULED_PROFILE_PUBLISH=true` repository variable.
  Publication proposes generated data/assets in a review-branch PR, rather
  than pushing `main` directly. Publishing job uses the ephemeral
  `GITHUB_TOKEN` with `contents: write` and `pull-requests: write`;
  no permanent PAT is required.

## Bot-created review PRs — required manual procedure

GitHub normally prevents `GITHUB_TOKEN`-created PR or push events from
automatically triggering new workflows. An owner should use
**Actions → Profile security and integrity → Run workflow** and
**Actions → CodeQL Advanced → Run workflow**, selecting the proposed
`automation/profile-refresh-...` branch for **both** runs.
Confirm successful jobs and their exact head SHA before merging the PR.
Do not bypass rules. Do not add new required CodeQL status checks until
the workflow is deployed, a review-branch dispatch is tested, and GitHub
recognizes its check contexts on the relevant PR commits.

## Reporting vulnerabilities privately

Report potential problems to the owner using
[Private vulnerability reporting](https://github.com/aymanbouanouj/aymanbouanouj/security/advisories/new)
**if the GitHub setting is enabled**, rather than publishing secrets,
attack demonstrations containing credentials, or private data in Issues.
If private reporting is unavailable, use the owner's public professional
contact method without including secret material.

## Secrets, permissions and dependency hygiene

Never commit passwords, tokens, recovery codes, private keys, `.env` or
sensitive backups. If a secret is exposed, **revoke/rotate it immediately**
before removing references; deleting a file does not clean Git history,
forks, cached copies or artifacts. Review GitHub account 2FA/passkeys,
third-party app permissions, collaborators, and the repository's
Dependabot, Secret Protection and Code Scanning alert settings manually.
Do not approve or merge unreviewed third-party PR code or workflows.

## Privacy and IP boundaries

`data/contributions.json` includes dated aggregate GitHub contribution
counts, potentially counting private activity without private repository
names or source code. It and prior commits are public. The owner's
branding (AB monogram with violet arrow) is covered by an authorship
notice, not a government-issued trademark registration. Public viewers
may clone, download and fork this repository. The absence of an
open-source license is not a technical copy-prevention mechanism.

## Audit limitations

Successful tests, Gitleaks and CodeQL scans do **not** establish a
zero-vulnerability guarantee. Gitleaks detects known secret patterns,
not arbitrary sensitive data; previous history and binary files may
need separate inspection. CodeQL alerts must be reviewed in GitHub
Security. A full manual penetration test, browser/mobile quality check,
independent security review and account-settings audit are outside
this repository's automated checks.

## Dependency updates and least-privilege improvements (2026-10-11)

- `.github/dependabot.yml` requests **reviewable weekly** GitHub Actions and pip
  version update PRs; there is no automatic merge or automatic approval.
- `requirements-ci.txt` tracks the pinned CairoSVG renderer, replacing
  inline `pip install` specifiers in the publishing workflow, so Dependabot
  can propose version bumps with normal tests.
- CodeQL checkout uses `persist-credentials: false`, an explicit time limit,
  and only `contents: read` plus `security-events: write`.
- Dependabot alerts, security updates, secret scanning, push protection, and
  account MFA **cannot be enabled or verified through this repository
  connection**. The owner must verify these in GitHub Settings.
- Never merge automated dependency PRs solely because Dependabot authored
  them. Check changelogs, exact SHA provenance, and CodeQL/Gitleaks results.

## Profile freshness and rendering limitations

GitHub READMEs cannot run arbitrary JavaScript or interactive client applications.
The profile uses verified, self-hosted PNGs for mobile compatibility, so the
images are static, not animated widgets or live counters.

Every PNG image URL now carries a truncated SHA-256 fingerprint from
`assets/mobile/manifest.json`. The refresh workflow recomputes URLs after
verifying the source SVG and rendered PNG, making new reviewed images use
a new URL rather than a potentially stale GitHub image cache entry.

Statistics remain dated GitHub-API snapshots. Scheduled verification is
read-only until owner opt-in, and generated data appears on the public
profile only after the reviewed Pull Request has passed required checks
and been merged. Live links point to GitHub activity and repositories.
A true interactive dashboard would need an independent hosted web page.
