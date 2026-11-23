# AB profile dashboard

## Preview and verify locally

Use Python 3.11 or later from the profile repository root. The renderer uses the same font subsetting engine as pyftsubset. The lock file pins fontTools and its wheel hashes.

~~~sh
python -m pip install --require-hashes --no-deps --only-binary=:all: -r requirements-dashboard.txt
python scripts/render_svg_cards.py --write-readme
python scripts/render_svg_cards.py --verify
python -m unittest discover -s tests -v
python scripts/validate.py
~~~

Generate a complete offline preview with the checked seed data. Open the HTML file directly in a browser. Its SVG images are embedded and its links open the original public destinations.

~~~sh
STATIC=1 python scripts/render_svg_cards.py --output ../profile-preview/cards --preview ../profile-preview/profile-preview.html
~~~

In PowerShell, set the environment variable for the render and clear it afterward.

~~~powershell
$env:STATIC = '1'
python scripts/render_svg_cards.py --output ../profile-preview/cards --preview ../profile-preview/profile-preview.html
Remove-Item Env:STATIC
~~~

The renderer also accepts a different validated input pair via `--calendar` and `--public`. Use `--verify` with those same paths to compare output to the input pair. Across platforms, verification compares the exact decompressed font tables when zlib encodings differ. The default seed files are `data/dashboard-contributions.json` and `data/dashboard-public.json`.

## Refresh and provenance

The existing **Refresh live public activity** workflow runs hourly. On its first successful scheduled run each UTC day, it reuses the verified GraphQL calendar, fetches public REST metadata, renders the live SVGs and validates them against the two JSON files. Relevant merges to `main` and a manual run on `main` also request a refresh. Scheduled runs retain a successfully verified same-day bundle. An unsuccessful refresh leaves the last published bundle available for a retry on the next hourly run.

The only automatic push target is `profile-live`. The workflow stages changed data files and SVGs under `cards/` alongside the existing `live/` artifacts. A GitHub default token suffices. Manually running the same workflow on a review branch rehearses the API-to-SVG build with read-only contents permission.

The complete calendar is checked for contiguous ISO dates, integer counts, a matching GitHub total and a recent UTC verification timestamp. The streak can end today or yesterday, which accommodates an incomplete day. The heatmap uses the actual date of every square and violet intensity bands for 0, 1–3, 4–7, 8–15 and 16 or more contributions. The fourth metric counts days with at least one contribution. The verified GraphQL calendar may include counts GitHub reports in aggregate.

The merged PR counter uses GitHub REST issue search for public merged pull requests authored by the profile owner. Repository counts come from exact public REST repository records. Upstream labels use confirmed PR merge or state metadata. The OWASP row links to the owner’s comment on the issue. The GitHub native graph provides the current activity view. [GitHub contribution fields](https://docs.github.com/en/graphql/reference/users#contributioncalendar) · [Public dashboard snapshots](https://github.com/aymanbouanouj/aymanbouanouj/tree/profile-live/cards)

## Public technical evidence

| Displayed technology or tool | Source |
| --- | --- |
| Laravel, PHP, MySQL, Vite, Tailwind CSS, Composer, Node.js and GitHub Actions | [Morocco2030 architecture and database](https://github.com/aymanbouanouj/morocco2030#architecture), [Composer manifest](https://github.com/aymanbouanouj/morocco2030/blob/main/composer.json), [Vite manifest](https://github.com/aymanbouanouj/morocco2030/blob/main/package.json), [CI workflow](https://github.com/aymanbouanouj/morocco2030/blob/main/.github/workflows/ci.yml) |
| JavaScript, HTML, CSS and Playwright | [AB Train Ticket Studio architecture](https://github.com/aymanbouanouj/ab-train-ticket-studio#engineering-and-architecture), [package manifest](https://github.com/aymanbouanouj/ab-train-ticket-studio/blob/main/package.json) |
| TypeScript, React and pnpm | [Understand-Anything contribution](https://github.com/Egonex-AI/Understand-Anything/pull/794), [dashboard dependencies](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/dashboard/package.json), [pnpm lockfile](https://github.com/Egonex-AI/Understand-Anything/blob/main/pnpm-lock.yaml) |
| Docker | [Gestion Vaccination CI container service](https://github.com/aymanbouanouj/gestion-vaccination/blob/main/.github/workflows/tests.yml) |
| Python | [This profile’s public contribution collector](https://github.com/aymanbouanouj/aymanbouanouj/blob/main/scripts/fetch_contributions.py) |
| PowerShell and Windows | [PC Full Check requirements](https://github.com/aymanbouanouj/PC-Full-Check#requirements) |

Technology badges reflect public repository evidence. The featured descriptions are based on the project READMEs. The active-work row uses GitHub’s last-push dates for the dashboard repository, the Understand-Anything fork and Gestion Vaccination. VioletGate fills the fourth public showcase slot. The train studio links to its working Pages demo. The profile links button opens the public link hub listed on the GitHub profile.

## Artwork and compatibility

- The AB mark reuses the owner-supplied silhouette in `scripts/brand_paths.py`. The profile composition uses the existing violet accents and Poppins typography found in the portfolio source. [Original profile](https://github.com/aymanbouanouj/aymanbouanouj/blob/e5cc7ba352f13c55b4ccb8d11008bce1afbcd0e3/README.md) · [Portfolio stylesheet](https://github.com/aymanbouanouj/portfolio-ayman/blob/0c8cfed539824a3b00005b5d27e5fb4a4a5ce2c8/style1.css)
- Poppins is distributed under the SIL Open Font License 1.1. The vendored upstream TTFs and license are in `assets/dashboard/fonts/`. Each image embeds only the glyphs and weights it uses and has an Arial and Helvetica fallback. [Pinned Poppins source](https://github.com/google/fonts/tree/7dc16b7de42db624b902f2292b68ed9e489e5053/ofl/poppins)
- The technical grids use Poppins Medium and Regular at sizes suited to their desktop and mobile layouts. Translucent text removes the colored antialiasing fringes observed in Chromium’s SVG rendering.
- Technology marks reuse licensed icon data. The grid centers each mark using its visible path bounds. The grid variants, including the standalone MySQL dolphin, record their sources in `assets/dashboard/tech-icons.json`. Devicon’s MIT notice is in `assets/dashboard/DEVICON-LICENSE.txt`. [Simple Icons license](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md) · [Devicon license](https://github.com/devicons/devicon/blob/54cfe13ac10eaa1ef817a343ab0a9437eb3c2e08/LICENSE)
- The train header crops owner-controlled artwork from the train studio. The renderer fingerprints it and embeds it as a JPEG with a vector fallback. The laptop, stadium and diagnostics scenes are original vectors. [Train artwork source](https://github.com/aymanbouanouj/ab-train-ticket-studio/blob/cf9983538e935262d23c47990f3f71ab4f2b24c7/public/fidelity/reference-hero.png) · [Artwork provenance](https://github.com/aymanbouanouj/ab-train-ticket-studio/blob/cf9983538e935262d23c47990f3f71ab4f2b24c7/docs/PUBLICATION-PROVENANCE.md)

Project, contribution and repository images are linked through their HTML anchors. GitHub controls the page width, navigation and native profile pins. The compact image variants are selected by browser viewport. The desktop image remains the fallback for clients that ignore responsive sources. The SVGs support reduced motion and use local resources. GitHub scheduling and image caching can delay visible updates.
