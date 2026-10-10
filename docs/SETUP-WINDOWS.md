# GitHub Profile v3.1 — Windows 11

## Status

This is a **local review draft**. It has not been uploaded to your GitHub account. The official AB + purple arrow mark was traced from a screenshot supplied by the account owner. For pixel-perfect brand fidelity, replace the traced paths using your original SVG logo later.

## Test the code

Open this folder in VS Code and PowerShell:

```powershell
py -3 .\scripts\validate.py
py -3 -m unittest discover -s tests -v
Start-Process .\docs\preview.html
```

The SVG images under `assets` show **AWAITING FIRST GITHUB SYNC** until real API data has been fetched. `docs/preview.html` is an illustrative local page, not GitHub itself. Demo counts belong only to a test fixture and never to the README assets. No mock numbers appear in the actual README.

## Publish only after approval

1. Sign in to GitHub and inspect whether `aymanbouanouj/aymanbouanouj` already exists. Do not overwrite an existing repository.
2. Create a **public** repo with exactly that name if it does not exist. A root `README.md` is mandatory.
3. Run tests and review the files and permissions. The workflow is manual-only at first.
4. Publish the files to the profile repo on a reviewed branch / pull request, or through your trusted authenticated Git terminal.
5. In **Actions**, trigger `Verify or publish contribution artwork`, keeping `publish=false` (default). This read-only job fetches and tests the latest public GitHub GraphQL contribution calendar **without committing it**. No PAT is required.
6. Compare the GitHub profile contribution calendar with the returned totals: the GraphQL GitHub App installation token may **exclude private/internal contributions**. The 81 figure seen in an earlier screenshot is not a validated API result; never substitute it manually.
7. If the read-only test passes, run the same workflow again with `publish=true`. This grants `contents: write` **only to the publish job**, and updates only the generated JSON and four stats SVGs. A branch protection rule may reject the push; do not bypass it.
8. Inspect the GitHub-rendered README (not just local HTML), dark/light themes, narrow screens, animation and motion-reduction, plus external project links.
9. Daily scheduled updates are deliberately **not installed** in v3.1. Decide separately after live validation and a permissions review.

## Git commands (only when GitHub repo exists and you approved publication)

```powershell
git init
git add .
git diff --cached --stat
git commit -m "feat: add original verified GitHub profile"
git branch -M main
git remote add origin https://github.com/aymanbouanouj/aymanbouanouj.git
git push -u origin main
```

**Do not execute the push sequence over an existing remote/repository.** For an existing repository, clone it first and review a pull request instead.

## Privacy, accuracy, and license

- Stats represent GitHub's contribution calendar, not a measure of skill or employment.
- Counts may include private-contribution aggregate depending on account settings; review before public publishing.
- The SVG artwork is newly authored for this user, using an owner-supplied brand screenshot, not another developer's files.
- No external badge service, advertising tracker, or third-party source runs in profile visitors' browsers.
- A small number of GitHub Actions steps use write permission solely to update validated snapshot + assets; action checkout pinned to reviewed commit.
- No generated code was imported from Avi Vashishta's repository.
