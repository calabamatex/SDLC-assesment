# Repository rename checklist (SDLC-034)

The repository name `SDLC-assesment` contains a typo (missing `s`). The remediation plan tracks the rename as a manual GitHub admin action; this document is the runbook.

## Steps

1. **Confirm on `main`**: ensure the working tree is clean and CI is green on `main`.
2. **GitHub UI rename**:
   - Navigate to `Settings → Repository name`.
   - Change `SDLC-assesment` to `sdlc-assessor` (case-sensitive).
   - Click `Rename`.
   - GitHub keeps an automatic permanent redirect from the old URL.
3. **Local clone update** (each contributor):
   ```bash
   git remote set-url origin git@github.com:calabamatex/sdlc-assessor.git
   ```
4. **Update internal references** — already done in this commit:
   - `README.md` clone URL
   - `SECURITY.md` advisory link
   - `CONTRIBUTING.md`
   - `pyproject.toml` `[project.urls]`
   The Python package name (`sdlc-assessor` in `pyproject.toml`) is already correct and does not need to change.
5. **Communicate**: post in the team channel and any external groups that referenced the old URL.
6. **Verify the redirect**:
   ```bash
   curl -sI https://github.com/calabamatex/SDLC-assesment | grep -i location
   ```
   Expect a `301` response pointing at the new URL.

## Why this is manual

Renaming a repository requires repository-owner privileges. The implementing agent does not have those credentials, and the action is durable (other internal links and bookmarks need to follow). Performing it deliberately, with a PR-time announcement, is safer than a scripted rename.

## What this commit already prepared

- All in-repo references to `sdlc-assessor` (the package) are correct.
- All references to the old `SDLC-assesment` repository name remain in the URL form `https://github.com/calabamatex/SDLC-assesment` until the rename, at which point GitHub will auto-redirect them. Update the canonical references in this commit if the rename has already been performed.
