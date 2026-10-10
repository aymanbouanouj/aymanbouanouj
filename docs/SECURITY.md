# Security and data handling notes

- Profile assets are self-hosted, inline-free SVG with CSS animation only; no JavaScript, external URL references, or third-party counter embeds.
- The fetcher calls **only** `https://api.github.com/graphql`; it does not scrape HTML or use an untrusted statistics API.
- Live data requires an ephemeral `GITHUB_TOKEN` scoped to this profile repository. There is no PAT stored in files.
- The legacy contribution workflow runs on manual dispatch only; the combined profile-refresh workflow also runs every six hours. The first `publish=false` run has read-only permissions and cannot push; `publish=true` separately grants write to its publish job after the verification job succeeds. A daily schedule is deliberately absent.
- The only workflow job requesting `contents: write` is `publish`, for updating its own generated artwork. The checkout action is first-party and pinned to a reviewed commit SHA. `persist-credentials: false` prevents leaving a token in Git config.
- GraphQL error/malformed data aborts without overwriting existing artwork.
- The API can include privately counted contributions if the user's contribution visibility setting exposes them in aggregate: inspect the data before publishing.
- Artifact generation validates consecutive ISO dates and numeric counts. Generated XML content uses escaped text. README and generated SVGs are scanned by local checks.
- No attempt is made to enumerate private repositories, files, organizations, contacts, or emails.
- Workflow push may be blocked by branch protection or repository policy, and must not be bypassed.
- As with any generated website artwork, review changes before publishing. Checks are a defense-in-depth measure, not a security audit guarantee.

## Accuracy contract (v3.1)

- Reject synthetic, stale (older than 36 hours), future-dated, invalid, inconsistent or wrong-user snapshots.
- Current streak is zero if neither today nor yesterday has a counted contribution; do not confuse an older historical streak with a current streak.
- Render the verified synchronization timestamp in the statistics panel to reveal when data stops refreshing.
- GraphQL `GITHUB_TOKEN` may not show privately counted contributions; never assert complete account totals until reconciled on GitHub.
- A read-only verification workflow may fail with API permission errors; stop and diagnose rather than silently replacing values or adding a personal token.
- The `README.md` does not claim that repository source availability necessarily means a license grants reuse rights.

## Automated public profile evidence (October 2026)

- Public language scans use GitHub Linguist; no private repository is scanned.
- Engineering tools are discovered only from public manifests and are not proficiency rankings.
- Project CI and release signals come from public GitHub APIs. A CI status is not a security certification.
- A single combined scheduled workflow updates contribution, language and engineering graphics every six hours; manual dry runs use read-only permissions. Scheduled writes and manual publish jobs share one concurrency group.
- Old Stats and Tech Stack individual workflows remain available manually only. Do not trigger publish concurrently.
- The project in focus is not automatically inferred from private activity. External merged PR evidence must link to the original PR.

## Release verification status — 2026-10-10

- The first combined refresh succeeded in GitHub Actions run 38088752616, including its offline tests, public API fetches, and generated-asset commit.
- Only recognized secret formats were screened across the 12 existing commit diffs. A pattern search cannot guarantee absence of all secrets.
- Social-account ownership, real-device rendering, and full history/content review remain release gates. Do not publish automatically.
