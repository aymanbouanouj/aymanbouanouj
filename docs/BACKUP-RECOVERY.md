# Independent backup and recovery

The profile is public; its Git history is not a substitute for an independent
backup. Keep backups outside GitHub, preferably on an encrypted external
drive and a second independent copy. Never commit a bundle or secret material.

## Windows / PowerShell — verified Git mirror and bundle

Use a destination folder on a drive with adequate free space. The example
creates a new timestamped directory, never overwrites an existing backup and
does not push to GitHub.

```powershell
$root = Read-Host "Existing backup folder on external/encrypted storage"
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw "Backup directory does not exist"
}
$root = (Resolve-Path -LiteralPath $root).Path
$folder = Join-Path $root ("GitHub-Profile-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
if (Test-Path -LiteralPath $folder) { throw "Backup already exists" }
New-Item -ItemType Directory -Path $folder -ErrorAction Stop | Out-Null
$mirror = Join-Path $folder "profile.git"
$bundle = Join-Path $folder "profile.bundle"
git clone --mirror https://github.com/aymanbounaouj/aymanbounaouj.git $mirror
if ($LASTEXITCODE -ne 0) { throw "Clone failed" }
git -C $mirror fsck --full
if ($LASTEXITCODE -ne 0) { throw "Git integrity check failed" }
git -C $mirror bundle create $bundle --all
if ($LASTEXITCODE -ne 0) { throw "Bundle creation failed" }
git -C $mirror bundle verify $bundle
if ($LASTEXITCODE -ne 0) { throw "Bundle verification failed" }
$refs = @(git -C $mirror for-each-ref --format="%(objectname) %(refname)" refs/heads refs/tags)
if ($LASTEXITCODE -ne 0 -or $refs.Count -eq 0) { throw "Ref listing failed" }
$refs | Set-Content -LiteralPath (Join-Path $folder "refs.txt") -Encoding UTF8
$hash = Get-FileHash -LiteralPath $bundle -Algorithm SHA256
$hash.Hash | Set-Content -LiteralPath (Join-Path $folder "profile.bundle.sha256") -Encoding ASCII
$hash
```

The mirror and bundle preserve fetched Git refs and reachable objects,
including main, profile-live, historic branches and tags. They do not
guarantee recovery of deleted/unreachable objects, Git LFS contents,
release attachments, Issues/PR discussions, settings or secrets.
Verify main/profile-live and expected historical branch refs in refs.txt.

## Additional private recovery inventory

Save separately, in private storage:

- Repository settings/ruleset JSON or sanitized screenshots, Actions default
  permissions, protection and alert settings. Include the ruleset ID.
- Secret **names and purpose only**, selected token permission categories,
  expiry/rotation plan and setup steps. Recreate or rotate secret values.
- Issue/PR records and release metadata if required for historical recovery.
- Original owner-supplied logos/design sources and approved screenshots.
- GitHub recovery codes in a password manager or encrypted offline location,
  separate from repository backups. Never include live tokens or private keys
  in a plaintext repository backup.

## Test recovery without writing to GitHub

Clone the bundle into a new empty test directory; use a mirror clone to
retain the branch refs. Run git fsck and compare branch/tag refs and the bundle
SHA-256 with the saved manifest. Inspect the current main and profile-live
files. Do not use a mirror push against the production repository.

For actual disaster recovery, first assess access/incident scope, then
restore to an isolated repository with actions disabled as appropriate.
Recreate protection, trusted secrets and verified workflow permissions.
Compare the approved source and data branch before enabling automation.
Restore production through reviewed changes and the existing branch rules.
Never merge profile-live into main.

## Historical refs policy

Production source is main; generated public data is profile-live. The
archive/, design/, older feature/, codex/, fix/, review/, refactor/,
automation/ and security/ refs record past work; preserve them. The
v5.0.0 release is historical, not the current dashboard. If a cleanup is
later approved, record each ref/SHA and verify the independent backup first.
No branch deletion or history rewrite is part of this maintenance procedure.
