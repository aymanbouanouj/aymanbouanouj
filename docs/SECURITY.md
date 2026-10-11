# Security and privacy policy

## Current posture
This repository is a personal GitHub profile. Treat every file, image, commit, generated statistic and workflow log as public material **before** making the repository public. Passing tests or a secret-pattern scan is not a guarantee of confidentiality.

## Reporting
Report suspected vulnerabilities privately to the repository owner using GitHub's private vulnerability reporting feature (if enabled). Do not publish credentials, tokens, proof-of-concept payloads containing secrets, or identifying personal data in public Issues.

## Actions and permissions
- `security-ci.yml` tests integrity and runs a pinned Gitleaks action with full Git history using read-only permissions.
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
