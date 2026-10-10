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
