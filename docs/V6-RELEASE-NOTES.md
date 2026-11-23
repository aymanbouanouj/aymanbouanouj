# Profile V6 — evidence-first presentation

## Scope

V6 is an incremental upgrade of the active V5 GitHub profile, not a new unrelated implementation. This change adds an original, self-contained SVG identity header; stronger section navigation; a concise evidence-linked engineering summary; a reduced primary social-link footprint with optional secondary links; and explicit provenance for private-repository aggregate language counts.

## Preserved behavior and safeguards

- The existing GraphQL/REST data collectors and `profile-live` data branch remain in place. The scheduled workflow now publishes additional verified V6 assets after the original data checks.
- No credentials, repository names, private code or private metadata are embedded in the README or new SVG.
- Private language statistics are an optional aggregate, not a proxy for private project disclosure.
- Existing four featured projects, their caveats, the native GitHub contribution-calendar caveat and historical assets remain available.
- No third-party image service, tracking pixel, client-side JavaScript or broadened publishing permission is introduced. A pinned Pillow build dependency processes real public project screenshots.
- `main` remains untouched until review and its required checks approve a PR.

## Review checklist

1. Check desktop and mobile GitHub README rendering (including dark and light GitHub themes).
2. Verify the self-hosted banner loads, alt text describes it and all navigation targets exist.
3. Run `python -m unittest discover -s tests -v` and `python scripts/validate.py`.
4. Confirm required Gitleaks, offline integrity and CodeQL checks pass on the exact PR head.
5. Inspect the dated `profile-live/live/portfolio.md` snapshot: do not confuse code-byte distribution with proficiency, and check that no private repository name appears.
6. Verify snapshot consistency and refresh after merge; do not call the charts real time.
7. Review social and demo URLs before final merge.

## Limitations

This PR does not replace the data pipeline, solve GitHub's best-effort scheduling/cache delay, guarantee security or verify rendering across devices. Future improvements should target durable usability checks and trustworthy presentation of verified project outcomes rather than more counters.

## V6 visual reference integration (22 November 2026)

The requested reference shows a dark GitHub-like dashboard, a glowing white AB/violet-arrow monogram, a neon purple developer banner, four evidence cards, a contribution calendar, compact language/framework grids, feature tiles, public work, and a footer. The active V6 branch now includes:

- Source-owned and SVG-safe neon circuit header: `assets/brand-v6.svg`
- User-provided AB logo optimized for GitHub README embedding: `assets/v6-logo-source.webp` (the original user image was not changed in place)
- Three original SVG feature illustrations: `assets/v6-project-*.svg`
- Four live generated illustrations: `live/v6-metrics.svg`, `live/v6-calendar.svg`, `live/v6-stack.svg`, and `live/v6-open-source.svg`
- Reusable deterministic renderer: `scripts/live_dashboard_v6.py`
- No changes to the external GitHub UI, default GitHub avatar or native pinned repositories

### Critical accuracy and rollout constraints

- GitHub does not let repository README content modify its navigation, profile sidebar, follow buttons, native tab bars, or pinned repositories. The visual reference is reproduced **inside README capabilities**, not as a GitHub interface skin.
- Values in the reference screenshot are **examples**, not evidence. New metrics use genuine GraphQL calendar totals, counted active days, **recent independently verified public external merged PRs**, and owner public original repository totals. Do not call the external PR sample a lifetime total.
- Private repository source, identifiers and branch details remain unpublished. Only already supported aggregated GitHub Linguist byte counts appear when the owner's optional credential works.
- The V6 image URLs have been bootstrapped onto `profile-live` with eight dated/verified SVG panels and three preview project images, fixing the previously broken draft PR links. The approved workflow will replace the bootstrap visuals with fully generated V6 panels and uniform source-backed PNG cards after merge. Existing V5 evidence remains available.
- GitHub Actions runs hourly on a best-effort basis. No claim of instant updates or guaranteed schedule is made.
- The real GitHub account avatar can only be changed by the account owner through GitHub profile settings; the README does not control it.

### Final verification before merge

1. Observe all four required jobs (offline integrity, full-history Gitleaks, CodeQL Python, CodeQL Actions) **on the final PR head SHA**.
2. Check source proof, absence of private names, actual value provenance and SVG rendering on desktop/mobile.
3. After merge, run the **Refresh live public activity** workflow on `main` if the first scheduled run has not arrived. Confirm all eight V6 SVG panels and three V6 project PNGs are regenerated from the current verified snapshots on `profile-live` before considering rollout finished.
4. Compare rendered V6 screenshots in GitHub light and dark, verify source links, respect image caching, and ensure no fabricated statistics.


## Reference-exact V6 README implementation

The visual reference is followed in the visible README, with the preserved V5 content moved into a collapsible evidence appendix. The full-width modules appear in this order:
1. branded hero and working public links;
2. four API-backed metric cards;
3. a GitHub GraphQL contribution grid;
4. twelve compact technology chips;
5. a seven-tool Frameworks / Build Tools strip;
6. three clickable featured repository cards;
7. verified merged external pull requests;
8. recently pushed public repositories;
9. four curated public repository selections;
10. original AB footer.

The top GitHub navigation, account sidebar, actual avatar, real native pinned section and Follow/Sponsor controls **cannot be modified** by a profile README. Decorative link labels drawn in a hero SVG are not independently clickable; the functional HTML links immediately following the banner serve those actions.

### Automatic real-image / placeholder policy

Each featured card is generated as an **actual PNG** by `scripts/live_project_cards_v6.py` after reading the following eligible **public** locations in its own repository, in priority order:

- `assets/profile-cover.png` (recommended upload path)
- `assets/profile-cover.jpg` or `assets/profile-cover.webp`
- `assets/profile-card.png`
- `media/readme/cover.png` or `media/readme/preview.png`
- `docs/screenshots/cover.png`
- Repository-specific existing real screenshots:
  - `morocco2030/docs/screenshots/01-home.png`
  - `ab-train-ticket-studio/media/readme/desktop-journey.png` or `media/readme/ticket-preview.png`
  - `PC-Full-Check/docs/screenshots/overview.png` if later added

**How to add a project cover:** upload a suitable real screenshot into the project's own public repository at `assets/profile-cover.png`; commit it to that repository's default branch. A subsequent successful hourly best-effort refresh discovers the GitHub blob SHA and regenerates the matching project card. A missing image is intentionally displayed as an empty styled cover area with its placeholder label. No stock photography or imagined project screenshots are published.

Security restrictions: read public GitHub REST data using an ephemeral GitHub Actions token; verify owner, repository privacy, default branch, fixed candidate paths, file size (≤2 MB), base64 contents, Git blob SHA-1, and raster type (PNG/JPEG/WebP). Pillow is pinned. Reject decompression bombs, unsafe input or a GitHub service error instead of silently publishing an invented screenshot. `v6-featured.json` records only public source paths, blob SHAs, card SHA256 digests and verified public star/fork counts; no private repository data.

### Real data versus screenshot examples

The reference's annual contributions, 36-day streak, 27 merged PRs and 414 private contributions are **not** hard-coded. V6 shows:
- contribution total from GitHub GraphQL over the calendar window,
- streak computed from the same validated calendar,
- size of independently verified recent public *external merged PRs*, not lifetime merges,
- original public repositories (instead of unsupported private contributions),
- owner-declared tools distinguished from verified GitHub Linguist code bytes and framework manifests.

The live-image paths are **already seeded** in the `profile-live` branch to eliminate broken draft PR images. On merge, the scheduled live generator replaces the seeds with fully verified current visuals. A read-only GitHub Actions gate (`scripts/check_live_asset_refs.py`) now fails PR checks if README references any missing live image. Merge only after all required checks and the actual rendered visual review pass. No third-party badge hosts, JavaScript or direct writes to protected `main` are involved.
