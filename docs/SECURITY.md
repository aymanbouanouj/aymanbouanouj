# Security policy — Ayman GitHub profile

## Current verified posture (2026-11-25)

This repository is public. The default branch `main` is protected by the
active [Protect Main ruleset (24860793)](https://github.com/aymanbounaouj/aymanbounaouj/rules/24860793).
At the audit baseline `df9e7cb7761586bad59a6a33c9e27396fb0a6603`:

- Branch deletion and non-fast-forward changes to main are blocked.
- A pull request and resolved review threads are required; no bypass actors.
- The four required checks are `Offline profile integrity`, `Full-history secret scan (Gitleaks)`, `Analyze (python)` and `Analyze (actions)`.
- Required reviewer approvals: zero; up-to-date status checks are not strictly required. This is not independent human approval. Maintainers must review the current head against current main before merging.
- Automatic branch deletion on merge is disabled. Historical branches remain public and must not be mistaken for supported production versions.

The [baseline integrity and secret-scan run](https://github.com/aymanbounaouj/aymanbounaouj/actions/runs/45364018880)
passed 121 tests and an explicit Gitleaks scan across all fetched reachable Git refs
(432 reachable commits reported by Git; 395 commits reported scanned by Gitleaks, no matching leaks).
[CodeQL](https://github.com/aymanbounaouj/aymanbounaouj/actions/runs/45508389362)
completed successfully for Python and Actions. A successful job is not proof
that the Security alerts inbox is empty. These are historical baseline results,
not a claim about every subsequent commit.

## Publication and trust boundaries

- `.github/workflows/profile-live.yml` runs on a best-effort hourly schedule
  (minute 37 UTC), relevant main pushes and manual dispatch. Only the trusted
  main publication job has contents write access. Its generated output goes
  to `profile-live`; it does not push main or automatically merge PRs.
- Technology evidence and the language portfolio are attempted hourly,
  independently of the daily dashboard metadata/calendar retention. The
  language-share SVG is derived from the final validated portfolio JSON and
  verified before staging. GitHub caching and delayed/dropped scheduled runs
  mean that displayed statistics are dated snapshots, not real-time counters.
- Public GitHub REST/GraphQL data and recognized public manifests are inputs;
  manifest content is inspected as data, not executed. Failed scans can
  retain previously verified snapshots. Read-only branch rehearsals do not
  receive the optional private-language token or publish production files.
- `profile-live` is deliberately writable by the publisher. Do not manually
  inject files or require PR approvals there without redesigning and testing
  the publisher. Its history remains public.
- `.github/workflows/profile-refresh.yml` maintains historical artwork.
  It is read-only by default; publishing requires explicit owner dispatch or
  the opt-in variable `ENABLE_SCHEDULED_PROFILE_PUBLISH=true`. It creates a
  review-branch PR rather than writing main. Do not enable the legacy
  publication path merely to refresh the current dashboard.
- External Actions use immutable full commit SHA pins. Production secrets
  are obtained from Actions secret/environment mechanisms, not committed.
  The ephemeral `GITHUB_TOKEN` authorizes publication; the derived Basic
  authorization value is explicitly masked before the push.

## Private language aggregates (optional owner opt-in)

`PRIVATE_LANGUAGE_TOKEN` is separate from the ephemeral publishing token.
It is passed only to the technology refresh step. The private collector
requests repository metadata and language byte counts; it does not fetch
private source files or manifests. It publishes language names, aggregate byte
counts/percentages and a private-aggregate evidence marker, not private
repository identities, paths, credentials or source.

Aggregates are intentionally public information and may permit inference about
private work, especially rare languages. Past generated snapshots are public
Git history. A retained snapshot can preserve old aggregates after an API
failure or a scope change; revocation alone does not erase history or forks.
If opting out, revoke/remove the token, confirm a successful refresh without
private access and verify the resulting public snapshots. If historical
aggregates themselves are sensitive, plan removal separately; never rewrite
history or delete archives without explicit owner authorization.

Owner-only token review:
1. Open [fine-grained tokens](https://github.com/settings/personal-access-tokens)
   and [Actions secrets](https://github.com/aymanbounaouj/aymanbounaouj/settings/secrets/actions).
2. Prefer a fine-grained token restricted to explicitly authorized owned
   repositories, with a finite expiry. GitHub documents Metadata: read for
   both listing accessible repositories and listing repository languages.
   Do not grant Contents, Administration or write permissions merely for
   language statistics. Verify actual compatibility with the selected repos
   and token type before revoking a working token.
3. Record only the purpose, permission categories, expiration and rotation
   procedure in a private recovery note. Do not save the token value in
   docs, shell history, chat, screenshots or backup reports. If rotating,
   update the Actions secret securely, verify the next run and revoke the old token.

[GitHub REST token permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)
and [repository language endpoint](https://docs.github.com/en/rest/repos/repos#list-repository-languages).

## Continuous security and dependency checks

- `security-ci.yml`: regression tests, sensitive tracked filename gate,
  SVG/PNG checks and an explicit Gitleaks `git --redact --log-opts="--all"`
  after full-history checkout. Known-pattern scanning cannot find every
  private value or historical binary disclosure.
- `codeql.yml`: Python and Actions analysis on main, PRs, schedule and
  manual dispatch; read-only contents, security-events write and no stored
  checkout credentials. Review actual open and dismissed alerts.
- Dependabot proposes reviewable weekly GitHub Actions and pip changes.
  Never auto-approve or merge solely because a bot authored a PR.
  Check release notes, immutable tag/commit provenance, current base and tests.
- Dashboard rendering dependency installation uses version and hash pins.
  The historical CairoSVG path has a direct version pin; its dependency
  closure deserves separate maintenance.

## Owner-only settings checklist (not verified by the audit connection)

- [Security and analysis settings](https://github.com/aymanbounaouj/aymanbounaouj/settings/security_analysis):
  verify secret scanning, push protection, dependency graph and Dependabot
  alerts/security updates where available.
- [Security alerts](https://github.com/aymanbounaouj/aymanbounaouj/security):
  inspect open and dismissed secret, dependency and code-scanning alerts.
- [Actions settings](https://github.com/aymanbounaouj/aymanbounaouj/settings/actions):
  prefer default read-only permissions; preserve explicit job permissions,
  review allowed actions, PR approval policy and workflow/secret access.
  The optional legacy PR-creation path needs separate testing if enabled.
- Review collaborators, installed apps and account
  [2FA/passkeys](https://github.com/settings/security) and
  [email privacy](https://github.com/settings/emails).
- Store recovery codes outside GitHub in an encrypted password manager
  or offline secure storage. Never send screenshots containing secret values.

## Review and recovery procedures

For a bot-created review PR, GitHub may not trigger normal checks from
`GITHUB_TOKEN`. Manually run **Profile security and integrity** and
**CodeQL Advanced** on the exact review branch, check the SHA and compare
with current main. For a dashboard generator change, also rehearse the
read-only live API build. Do not bypass protections.

See [release checklist](RELEASE-CHECKLIST.md) and
[backup and recovery guide](BACKUP-RECOVERY.md). Backups must remain outside
this public repository. Retain historic refs without merging them into
production; restore through a reviewed branch and ordinary protection gates.

## Reporting and incident response

If a secret is exposed, revoke/rotate it immediately, assess usage and
affected scopes, then plan history/cache/fork/artifact remediation. Deleting
a file in a new commit is insufficient. Do not post secrets in Issues.
Use [private vulnerability reporting](https://github.com/aymanbounaouj/aymanbounaouj/security/advisories/new)
if enabled, or the owner's published professional contact without secret values.

Public viewers may clone and fork the repository. The rights notice reserves
original branding and artwork but is not technical copy prevention or
proof of trademark registration. See [NOTICE](../NOTICE.md).

## Audit limitations

No absolute security guarantee is possible. The 2026-11-25 review covered
repository settings visible through the connection, current main/live data,
known secret patterns, branch-head filenames, and selected historical and
binary checks. Account settings, token scope/expiry, private Security alerts,
all historical image contents, unreachable Git objects, external copies and
full independent penetration testing were not verified. No secret values
should be collected to complete those checks.
