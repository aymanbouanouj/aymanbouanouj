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
