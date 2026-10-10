# Profile maintenance on Windows 11 (October 2026)

The private repository now exists and is synchronized through GitHub Actions. Do not reinitialize Git or recreate the repository.

```powershell
cd C:\Users\HP\Desktop\aymanbouanouj
git status --short
git pull --ff-only origin main
py -3 -m unittest discover -s tests -v
py -3 .\scripts\validate.py
py -3 .\scripts\tech_stack.py --verify
py -3 .\scripts\engineering.py --verify
```

GitHub Actions: `profile-refresh.yml` is scheduled four times daily at 02:23, 08:23, 14:23 and 20:23 UTC (best-effort timing), with manual verification available through `publish=false`. The legacy per-component workflows remain manual-only. Read the run logs before treating the update as verified.

To review changes, inspect the rendered README on GitHub and test both Light and Dark themes. Before making the repository public, inspect all files and history, confirm external account ownership, and test a narrow/mobile viewport. Public release is a separate approval.

No Personal Access Token or local secrets are needed for these local tests.
