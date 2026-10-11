# Security and privacy policy

## Current posture
This repository is a personal GitHub profile. Treat every file, image, commit, generated statistic and workflow log as public material **before** making the repository public. Passing tests or a secret-pattern scan is not a guarantee of confidentiality.

## Reporting
Report suspected vulnerabilities privately to the repository owner using GitHub's private vulnerability reporting feature (if enabled). Do not publish credentials, tokens, proof-of-concept payloads containing secrets, or identifying personal data in public Issues.

## Actions and permissions
- `security-ci.yml` tests integrity and runs a pinned Gitleaks action for changed commits, plus an explicit command-line Gitleaks scan with `--log-opts="--all"` covering all locally reachable commit history, using read-only permissions.
- `profile-refresh.yml` is the only publication workflow. Verification runs read-only.
- Manual publication requires selecting `publish=true`. Scheduled publication is **disabled by default** unless repository Actions variable `ENABLE_SCHEDULED_PROFILE_PUBLISH` equals `true`.
- The publish job alone requests `contents: write`. It uses the ephemeral GitHub Actions token to push strictly generated artwork and data.
- Third-party dependencies and action SHAs require review before upgrades. No persistent PAT is required.
- Do not run workflows with untrusted pull-request code using write credentials.

## Privacy warning: contribution calendar
`data/contributions.json` and the derived contribution artwork may contain daily GitHub contribution totals, potentially including private contribution counts as exposed by GitHub GraphQL. Even after deleting the file later, prior commits can retain its data. The owner has expressly approved displaying this GitHub contribution-calendar data, **including aggregate private contribution counts if GitHub returns them**. This approval covers the data display only; it does **not** authorize changing the repository visibility. Private repository names, source code, credentials and metadata beyond the calendar must never be fetched or published.

For a later change toward maximum privacy, publish only static branding and public-repository information and omit contribution snapshots/graphics. Doing so requires a separate coordinated README, generator, and history policy change. Removing a file from the current commit is NOT history erasure.

## Source validation
GitHub project language/framework evidence comes from publicly accessible repositories; it is not a verified competence score. SVG files prohibit scripts, event handlers and remote dependencies. PNG files are checked against a SHA-256 manifest for their SVG sources. Synthetic fixture data is never used as live activity. Third-party social links should be confirmed manually.

## Release gates
1. Complete a secret scanner run over all refs and review any findings without exposing secret values.
2. Review daily contribution disclosure, linked accounts, licensing, logo rights and README claims.
3. Check repo settings: branch rules, contributors, Actions permissions, private forks, secret scanning and Dependabot.
4. Verify full test suite, mobile rendering and links.
5. Obtain explicit owner approval for Public visibility. Remain Private until approval.

## Limitations
Prior manual inspection found no recognizable credentials in 22 textual commit diffs, but binary blobs and unexpected secret formats were not exhaustively checked. Gitleaks and repository settings should be reviewed separately. If a real secret is found, revoke/rotate it before considering history cleanup.

## Repository configuration still requiring owner review

- The latest checks show `main` is not protected, and `allow_forking` is enabled for this private repository.
- GitHub's ruleset endpoint returned an upgrade-or-public limitation on the current private repository; protection cannot be considered configured. Apply a compatible branch rule once GitHub permits it, and ensure it does not block the generated-asset publisher.
- The connected GitHub application cannot read or change collaboration access, Actions repository variables, or all security-alert settings. Those must be reviewed under GitHub Settings by the repository owner.
- Scheduled publication still requires `ENABLE_SCHEDULED_PROFILE_PUBLISH=true`; disclosure approval does not silently opt in to unattended writes.

## Bilingual professional profile and main-branch controls

- The README intentionally presents English and French text together. The graphical panels retain their tested terminal layout and accessible English alt text; surrounding content explains the visuals in both languages.
- The publication workflow now checks `github.ref == 'refs/heads/main'` at job dispatch and `GITHUB_REF` before committing. This prevents a manual run from another branch from writing that branch's content into main.
- These workflow checks **are not branch protection**. A collaborator with Git push permission could still push code directly or force-push unless GitHub's branch protection or rulesets are enabled.
- While this private repository's Rulesets API reports a Pro-or-Public limitation, do not change visibility without final owner permission. Once available, configure main to block force pushes and deletion, and choose required PR reviews/checks in a way compatible with the generated-asset publisher.

## Manual workflow publication identity guard

The manual `publish=true` dispatch is restricted in the workflow to `github.actor == 'aymanbouanouj'`, and the shell step separately checks `GITHUB_ACTOR` before pushing. Scheduled publishing remains disabled by default and may be enabled only through `ENABLE_SCHEDULED_PROFILE_PUBLISH`. These checks are defense in depth **only**: anyone with sufficient repository write privileges can potentially modify workflows, and they are not a substitute for an active GitHub ruleset and least-privilege collaborators. After making the repository public, activate branch rules in Settings before accepting changes. Require protected history, no force pushes or deletion, and security CI; then revise the bot direct-push workflow if the chosen rules block it.

## Proposed PR-only generated updates
The publication job proposes refreshed README and generated assets on a unique `automation/profile-refresh-<run-id>-<attempt>` branch and opens a Pull Request; it does **not** push to `main`. The owner must review and merge after the security workflow passes. Repository Settings → Actions → General may need "Allow GitHub Actions to create and approve pull requests" enabled. Pull requests created using `GITHUB_TOKEN` ordinarily do **not** trigger `push` or `pull_request` workflows automatically. The owner must manually dispatch the existing `Profile security and integrity` workflow (using `workflow_dispatch`) on the proposed PR's source branch and verify both jobs passed for its exact head commit before merging. Do not mistake an earlier green run on main for verification of the proposed changes. Do not give the automation any bypass permission. Requiring a PR on `main` can be enabled **after this change is merged**. The repo's currently active ruleset still only blocks deletion and force pushes.
