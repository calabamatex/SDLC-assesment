# Repository rename runbook (SDLC-034) — completed 2026-04-25

The repository was renamed from `calabamatex/SDLC-assesment` (typo, missing `s`) to `calabamatex/sdlc-assessor` on 2026-04-25 as part of the v0.2.0 follow-up. GitHub keeps a permanent 301 redirect from the old URL, so external links and existing clones continue to work.

This document is preserved as a runbook in case the project ever needs to be renamed again, and as the durable record that the rename happened.

## Steps that were taken

1. **Confirmed `main` was clean** with v0.2.0 already tagged and CI green.
2. **Renamed via `gh`**:
   ```bash
   gh repo rename sdlc-assessor --yes
   ```
   GitHub records the rename and stands up a permanent redirect at `https://github.com/calabamatex/SDLC-assesment` → `https://github.com/calabamatex/sdlc-assessor`.
3. **Updated the local clone**:
   ```bash
   git remote set-url origin git@github.com:calabamatex/sdlc-assessor.git
   ```
4. **Verified the redirect**:
   ```bash
   curl -sI https://github.com/calabamatex/SDLC-assesment | grep -i ^location
   # location: https://github.com/calabamatex/sdlc-assessor
   ```
5. **Updated in-code references** to the new URL — `README.md` clone command, `CONTRIBUTING.md` clone command, `SECURITY.md` advisory link, `pyproject.toml` `[project.urls]`, `PLANS.md` design-record cross-reference. Historical design documents (`docs/ANALYSIS.md`, `docs/ACTION_PLAN.md`) intentionally were not rewritten — their references reflect the repo's name at the time those documents were authored, and are preserved as part of the audit trail. GitHub's redirect handles the URLs.
6. **Did not touch `pyproject.toml [project].name`** — the package name was already `sdlc-assessor` (correct) before the rename. The Python package distribution name and the repository name are now in sync.

## Why this was a manual / one-off action

`gh repo rename` requires admin privileges on the repository. The implementing automation does not run with those privileges; the rename was performed by the repo owner. After the rename, the URL surface area is small enough that updating in-code references is a single follow-up commit.

## What an external consumer should expect

- Existing clones keep working — `git fetch` against the old URL hits the redirect transparently.
- Existing PR / issue URLs keep working.
- Existing v0.2.0 [Release URL](https://github.com/calabamatex/SDLC-assesment/releases/tag/v0.2.0) keeps working via redirect; the canonical URL is now [`https://github.com/calabamatex/sdlc-assessor/releases/tag/v0.2.0`](https://github.com/calabamatex/sdlc-assessor/releases/tag/v0.2.0).
