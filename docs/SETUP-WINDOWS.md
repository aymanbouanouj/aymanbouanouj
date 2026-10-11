# Windows 11 — secure local maintenance

Use PowerShell from your existing cloned repository folder; **do not** recreate or reinitialize the repository.

```powershell
Set-Location (Join-Path $HOME 'Desktop/aymanbouanouj')
git status --short
git pull --ff-only origin main
py -3 -m unittest discover -s tests -v
py -3 .\scripts\validate.py
py -3 .\scripts\mobile_png.py --verify
```

## Full-history secret scan
The error `gitleaks : The term 'gitleaks' is not recognized` means Gitleaks is not installed or is not on PATH. Install it from the official [Gitleaks releases](https://github.com/gitleaks/gitleaks/releases), verify the release and executable before using it, then reopen PowerShell. No PAT or secrets are required for a local scan.

```powershell
gitleaks version
git fetch --all --prune
gitleaks git --redact --log-opts="--all" --report-format json --report-path "$env:TEMP\profile-secret-scan.json" .
```

Do not paste raw scan reports or suspected secret values into chats or issues. Keep reports outside Git. `exit code 1` normally means findings and must be reviewed, not suppressed by an allowlist without justification.

## GitHub Actions
The consolidated profile refresh remains on a six-hour schedule for read-only verification. Scheduled **writes are disabled by default**; to explicitly enable them the owner must set Actions repository variable `ENABLE_SCHEDULED_PROFILE_PUBLISH=true` after reviewing contribution privacy. Manual refresh defaults to `publish=false`.

Use GitHub Settings to inspect collaborators, Private Forking, secret scanning/Dependabot, Actions defaults and branch protection. These cannot all be changed by the limited GitHub connector.

Do not make the repository Public before the release checklist is complete and the owner explicitly authorizes that visibility change.

## Owner-only pre-public checks

1. Open the repository's **Settings > Collaborators and teams** and review every account with access. Remove any no-longer-needed collaborators.
2. In **Settings > General**, review private forking and disable it if unnecessary. If that option is unavailable, record the limitation.
3. Under **Settings > Actions > General**, limit Actions permissions to those needed for the consolidated publisher and check the default `GITHUB_TOKEN` permissions.
4. Check **Settings > Security & analysis** for private vulnerability reporting, Dependabot alerts, and secret scanning where available for the plan.
5. Check **Settings > Rules > Rulesets** or branch protection. The GitHub API currently reports a Pro-or-public limitation for rulesets on this private repository; avoid changing visibility as a workaround before final approval.
6. Test each social link while logged into your own account, and check mobile rendering.

**Scheduled publication option:** To allow periodic writes after the owner explicitly opts in, create the repository variable `ENABLE_SCHEDULED_PROFILE_PUBLISH` with value `true` under **Settings > Secrets and variables > Actions > Variables**. Without this, the six-hour run verifies but does not publish.

None of the steps above require uploading passwords, tokens, screenshots of private settings or personal data to this repository.
