# v3.1 verification report — 2026-10-10 (UTC)

## Passed locally

- 24 Python unit/regression tests, including stale streaks, malformed API responses, SVG validation and rejecting synthetic publish input.
- Eight SVG files parsed as XML; eight rendered as static PNG using CairoSVG in dark and light variants.
- GitHub Actions YAML parsed; `verify` job uses read-only contents permission; publish job requires explicit `publish=true` input and uses scoped write permission.
- Local preview alert text contrast in dark: 14.08:1; light: 12.17:1 (WCAG luminance formula, calculated on declared colors).
- Project repositories, quality/CI workflow endpoints, Windows test directory, and demos checked against public GitHub sources.
- Source files compile under the container's Python runtime; no third-party Python packages are required by the project scripts.

## Not yet verified

- Live GraphQL access from the owner's GitHub Actions `GITHUB_TOKEN`.
- Parity of visible GitHub contribution totals with GraphQL totals, particularly private contributions.
- Rendering on the real GitHub Profile README page and live mobile viewport. Chromium-based preview navigation is restricted in this execution environment; static SVG rendering was used instead.
- A successful publish job; no repository was created or changed.

## Safe release sequence

1. Inspect files and run local unit tests on Windows 11.
2. Create or inspect your public profile repository, and review a PR before any publish to main.
3. Run the GitHub Actions manual workflow with `publish=false` to verify the API without writing.
4. Compare returned totals with GitHub profile activity; investigate discrepancies.
5. If satisfied, manually run `publish=true` and inspect the resulting diff.
6. Review mobile/dark/light GitHub rendering before calling release complete.
