# Windows 11 — safe synchronization of GitHub Profile V5

The repository is public and `main` is protected. Never run `git reset --hard`, delete your clone, or merge the generated `profile-live` branch into `main`.

## Step 1 — Inspect the existing local clone

From PowerShell inside your existing repository (do not assume its path):

```powershell
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
git fetch origin main
git log --oneline --left-right HEAD...origin/main
```

Review this output **before** changing files. A dirty working tree or divergent commits require separate preservation and review.

## Step 2 — Synchronize only if safe

If currently on `main`, the working tree is clean, and the branch can fast-forward:

```powershell
git pull --ff-only origin main
py -3 -m unittest discover -s tests -v
py -3 .\scripts\validate.py
py -3 .\scripts\mobile_png.py --verify
```

Do not force the pull if it fails.

## Two distinct refresh pipelines

- **V5 current profile:** `.github/workflows/profile-live.yml`, automatically checked every hour at minute 37 UTC (best effort) and after relevant protected-main updates. Writes validated JSON, Markdown and SVG **only** to `profile-live`, using an ephemeral GitHub Actions token. It needs no manual `Run workflow` in normal operation.
- **Historical artwork:** `.github/workflows/profile-refresh.yml`, read-only verification four times per day. Optional generated-asset review PRs require explicit opt-in via `ENABLE_SCHEDULED_PROFILE_PUBLISH=true`. This variable is **not necessary** for V5 automatic updates.

GitHub schedules can be delayed or disabled and image caches can lag. SVG graphics are automatically refreshed snapshots, not instantaneous interactive widgets. On each live publish, Markdown is reconciled against retained JSON and every final artifact is verified before push.

## Optional local full-history secret scan

Install [Gitleaks](https://github.com/gitleaks/gitleaks/releases) from the official release, then:

```powershell
gitleaks version
gitleaks git --redact --log-opts="--all" --report-format json --report-path "$env:TEMP\profile-secret-scan.json" .
```

Keep results outside the repository. Never paste actual secret values into chats or issues.

## Owner-only account review

In GitHub Settings, review collaborators, installed apps, default Actions permissions, MFA, Dependabot/CodeQL/Secret Scanning alerts and push protection. A passing CI run alone cannot verify those account-specific settings.
