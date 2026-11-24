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

The renderer accepts alternative snapshots via `--calendar`, `--public` and `--technology`. Use `--verify` with the same paths to compare the SVGs against those inputs. Across platforms, verification compares the exact decompressed font tables when zlib encodings differ. The default seeds live in `data/dashboard-contributions.json`, `data/dashboard-public.json` and `data/dashboard-technology.json`.

## Portfolio launch link

The README intentionally displays exactly two hero CTAs: **Profile links** (the verified Beacons link) and **Portfolio** (visibly marked Coming soon and not clickable before launch). There is no placeholder, invented deployment, or redirect for Portfolio.

Once the real portfolio is live, open `scripts/render_svg_cards.py` and set `PORTFOLIO_SITE_URL` to the real `https://...` address, then run `python scripts/render_svg_cards.py --write-readme`, run tests and review the draft before publishing. The Portfolio image is individually wrapped in an HTML anchor only when a URL is configured. An SVG embedded through `<img>` cannot expose separate clickable regions inside the hero banner, so these two standalone cards sit immediately beneath it.

## Refresh and provenance

The existing **Refresh live public activity** workflow discovers technologies on every hourly run. Calendar, metrics and activity cards can reuse their verified same-day bundle independently. Relevant merges and manual runs on `main` request a refresh as well. Before publishing, the workflow validates the final 17 SVGs against the three published JSON snapshots.

The only automatic push target is `profile-live`. The workflow stages changed data files and SVGs under `cards/` alongside the existing `live/` artifacts. A GitHub default token suffices. Manually running the same workflow on a review branch rehearses the API-to-SVG build with read-only contents permission.

The complete calendar is checked for contiguous ISO dates, integer counts, a matching GitHub total and a recent UTC verification timestamp. The streak can end today or yesterday, which accommodates an incomplete day. The heatmap uses the actual date of every square and violet intensity bands for 0, 1–3, 4–7, 8–15 and 16 or more contributions. The fourth metric counts days with at least one contribution. The verified GraphQL calendar may include counts GitHub reports in aggregate.

The merged PR counter uses GitHub REST issue search for public merged pull requests authored by the profile owner. Repository counts come from exact public REST repository records. Upstream labels use confirmed PR merge or state metadata. The OWASP row links to the owner’s comment on the issue. The GitHub native graph provides the current activity view. [GitHub contribution fields](https://docs.github.com/en/graphql/reference/users#contributioncalendar) · [Public dashboard snapshots](https://github.com/aymanbounaouj/aymanbounaouj/tree/profile-live/cards)

## Public technical evidence

`scripts/dashboard_technology.py` reuses V5’s paginated public repository inventory and language checks. It discovers new owned repositories automatically and excludes archived, disabled and forked projects. The profile’s own automation is eligible for the dashboard badges. It stays outside the V5 portfolio’s project language ratios. The hourly job collects each repository’s languages and recognized public files once and uses those observations for both dashboard and V5 artifacts.

- Positive GitHub Linguist results provide language evidence. Package manifests and lockfiles provide evidence for recognized dependencies, frameworks, runtimes and package managers. Dockerfiles, Compose files, CI workflows and committed example database settings provide infrastructure evidence. Manifests are read as data at the recorded public commit. [Composer example](https://github.com/aymanbounaouj/morocco2030/blob/main/composer.json) · [Database example](https://github.com/aymanbounaouj/morocco2030/blob/main/.env.example) · [CI example](https://github.com/aymanbounaouj/gestion-vaccination/blob/main/.github/workflows/tests.yml)
- The snapshot distinguishes owned projects from the scoped dashboard dependency evidence for the verified Understand-Anything contribution. It records source references. The optional existing `PRIVATE_LANGUAGE_TOKEN` is used only by the V5 aggregate collector. The dashboard records a language and a private-aggregate marker. V5 continues to publish aggregate language totals. Private repository names, paths, manifests and credentials stay out of both outputs. [Understand-Anything contribution](https://github.com/Egonex-AI/Understand-Anything/pull/794)

New snapshots keep the approved ordering and append additional verified entries in alphabetical order. Each grid adds rows as needed, with six desktop stack columns and seven desktop tools columns. Labels can wrap within a badge and a generic code icon covers languages with no verified mark. A badge represents repository evidence. Successful scans remove entries whose last proof disappeared, and a successful empty scan shows an empty state. An incomplete or failed scan reuses the last validated snapshot or the checked-in seed. Version 1 snapshots reproduce their published artwork during migration and fallback.

The workflow renders both sizes of both grids from `cards/technology.json`. The release README uses the live calendar and both technology grids, in both sizes, from `profile-live/cards/`. The calendar and metrics come from the same contribution snapshot. The release switch retains its historical CLI name: `python scripts/render_svg_cards.py --write-readme --live-technology`. Subsequent regeneration preserves that source selection. The checked-in SVGs and JSON remain reproducible offline seeds, not the published live sources.

Before release, verify that all six live SVGs and the technology snapshot exist and correspond to the validated source data; the source branch must pass the integrity and security checks. The publisher remains restricted to `main` and only writes the data branch. The pre-merge workflow on a draft branch is read-only; after an approved merge, confirm the first successful publisher run on `main` and the resulting data-branch commit. Never enable writes from draft branches.

After the username migration merges, the first successful refresh publishes `cards/building-aymanbounaouj.svg` on `profile-live`. Check the new raw SVG URL after that run. The published file under the former name stays on the branch for historical access.

The featured descriptions and engineering evidence come from the project READMEs. Recently Updated Projects uses GitHub’s last-push dates for the dashboard repository, the Understand-Anything fork and Gestion Vaccination. More Repositories links to VioletGate and Ayman Calc. Featured and additional repository cards are versioned locally. Contribution metrics and last-push dates use the live workflow. The train studio links to its working Pages demo. The Profile links button opens the public link hub listed on the GitHub profile.

## Artwork and compatibility

- The AB mark reuses the owner-supplied silhouette in `scripts/brand_paths.py`. The profile composition uses the existing violet accents and Poppins typography found in the portfolio source. [Original profile](https://github.com/aymanbounaouj/aymanbounaouj/blob/e5cc7ba352f13c55b4ccb8d11008bce1afbcd0e3/README.md) · [Portfolio stylesheet](https://github.com/aymanbounaouj/portfolio-ayman/blob/0c8cfed539824a3b00005b5d27e5fb4a4a5ce2c8/style1.css)
- Poppins is distributed under the SIL Open Font License 1.1. The vendored upstream TTFs and license are in `assets/dashboard/fonts/`. Each image embeds only the glyphs and weights it uses and has an Arial and Helvetica fallback. [Pinned Poppins source](https://github.com/google/fonts/tree/7dc16b7de42db624b902f2292b68ed9e489e5053/ofl/poppins)
- The hero, section headings and technical grids use grayscale antialiasing in Chromium through a near-opaque text layer. The embedded Poppins subsets include regular, medium, semibold and bold for the text that uses those weights.
- Technology marks reuse licensed icon data. The grid centers each mark using its visible path bounds. The grid variants, including the standalone MySQL dolphin, record their sources in `assets/dashboard/tech-icons.json`. Devicon’s MIT notice is in `assets/dashboard/DEVICON-LICENSE.txt`. [Simple Icons license](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md) · [Devicon license](https://github.com/devicons/devicon/blob/54cfe13ac10eaa1ef817a343ab0a9437eb3c2e08/LICENSE)
- The hero’s layered developer system, stadium and diagnostics scenes are original vectors. The train header crops owner-controlled artwork from the train studio. The renderer fingerprints it and embeds it as a JPEG with a vector fallback. [Train artwork source](https://github.com/aymanbounaouj/ab-train-ticket-studio/blob/cf9983538e935262d23c47990f3f71ab4f2b24c7/public/fidelity/reference-hero.png) · [Artwork provenance](https://github.com/aymanbounaouj/ab-train-ticket-studio/blob/cf9983538e935262d23c47990f3f71ab4f2b24c7/docs/PUBLICATION-PROVENANCE.md)

Project, contribution and repository images are linked through their HTML anchors. GitHub controls the page width, navigation and native profile pins. The compact image variants are selected by browser viewport. The desktop image remains the fallback for clients that ignore responsive sources. The SVGs support reduced motion and use local resources. GitHub scheduling and image caching can delay visible updates.
