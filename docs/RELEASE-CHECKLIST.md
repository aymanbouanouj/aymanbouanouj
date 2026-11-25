# Profile — security and maintenance checklist

Updated: 2026-11-25. Baseline: `df9e7cb7761586bad59a6a33c9e27396fb0a6603`.

## Baseline verified

- [x] Public repository, protected main, ruleset 24860793, no bypass actors.
- [x] Four required checks passed for the approved baseline: offline integrity, full-history Gitleaks, Python CodeQL and Actions CodeQL.
- [x] 121 baseline tests; PR #48 publication succeeded and the language chart matches the verified JSON.
- [x] Production updates only profile-live; current artwork and historical branches preserved.
- [x] 49 branches retained; one historical release v5.0.0. No automatic branch deletion.

## Before each merge

- [ ] Compare the exact PR head with current main; investigate conflicts and stale checks.
- [ ] Check that all four required contexts pass for that exact head; review actual security alerts.
- [ ] Confirm pinned action provenance and upstream release notes for dependency updates.
- [ ] Rehearse live API rendering read-only when changing generation/publishing logic.
- [ ] Verify no unintended README, brand, artwork, secret-scope or permissions changes.
- [ ] After merging relevant changes, confirm successful production publication and check final SVG/JSON consistency; scheduled execution and image caching remain best-effort.

## Owner-only verification

- [ ] Verify Secret Scanning and Push Protection settings and review all security alerts.
- [ ] Review Dependency Graph, Dependabot alerts and security updates.
- [ ] Review the optional PRIVATE_LANGUAGE_TOKEN scope, expiry and rotation; no secret values in reports.
- [ ] Review account 2FA/passkeys, email privacy, apps, collaborators and Actions permissions.
- [ ] Verify and store a complete independent Git mirror/bundle outside this public repository; see [backup guide](BACKUP-RECOVERY.md).
- [ ] Consider strict up-to-date required checks separately. Do not change profile-live protection without testing unattended publication.

## Historical refs

Keep prior designs and PR branches as historical evidence. Do not merge an
obsolete design branch into main merely to clean up the branch list.
Read [security policy](SECURITY.md) for limits and incident response.
