# Profile V6 — evidence-first presentation

## Scope

V6 is an incremental upgrade of the active V5 GitHub profile, not a new unrelated implementation. This change adds an original, self-contained SVG identity header; stronger section navigation; a concise evidence-linked engineering summary; a reduced primary social-link footprint with optional secondary links; and explicit provenance for private-repository aggregate language counts.

## Preserved behavior and safeguards

- The existing `profile-live` data branch, scheduled refresh workflow and GraphQL/REST collectors are unchanged.
- No credentials, repository names, private code or private metadata are embedded in the README or new SVG.
- Private language statistics are an optional aggregate, not a proxy for private project disclosure.
- Existing four featured projects, their caveats, the native GitHub contribution-calendar caveat and historical assets remain available.
- No new third-party image service, tracking pixel, JavaScript, runtime dependency or publishing permission is introduced.
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
- The four new SVGs are not present on the `profile-live` data branch until the updated workflow publishes them after merge, so they may appear missing in PR preview. Existing V5 assets and original evidence remain available during rollout.
- GitHub Actions runs hourly on a best-effort basis. No claim of instant updates or guaranteed schedule is made.
- The real GitHub account avatar can only be changed by the account owner through GitHub profile settings; the README does not control it.

### Final verification before merge

1. Observe all four required jobs (offline integrity, full-history Gitleaks, CodeQL Python, CodeQL Actions) **on the final PR head SHA**.
2. Check source proof, absence of private names, actual value provenance and SVG rendering on desktop/mobile.
3. After merge, run the **Refresh live public activity** workflow on `main` if the first scheduled run has not arrived. Confirm all four `live/v6-*.svg` files on `profile-live` before considering rollout finished.
4. Compare rendered V6 screenshots in GitHub light and dark, verify source links, respect image caching, and ensure no fabricated statistics.
