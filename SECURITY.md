# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |
| < 0.1.0 | no |

The `sdlc-assessor` codebase is pre-1.0. The supported version is the most recent minor release on `main`.

## Reporting a vulnerability

If you find a security issue in `sdlc-assessor`, **do not file a public GitHub issue.** Email the maintainer at the contact below with:

- A description of the vulnerability
- Steps to reproduce (input that triggers the issue, expected vs observed behaviour)
- The version (`sdlc --version` output) and Python version
- Any proof-of-concept code

**Contact:** open a private security advisory via [GitHub Security Advisories](https://github.com/calabamatex/SDLC-assesment/security/advisories/new), or email `security@calabamatex` (replace with the project's actual security contact in your fork).

## Disclosure timeline

- **Within 72 hours:** acknowledgement of the report.
- **Within 7 days:** initial impact assessment and triage decision.
- **Within 30 days:** fix released as a patch version, or public coordination plan if more time is required.
- **After fix:** advisory published with credit to the reporter (unless you prefer to remain anonymous).

## Scope

In scope:

- The `sdlc_assessor` Python package and its CLI.
- The CI workflows under `.github/workflows/`.
- The detector packs (`sdlc_assessor/detectors/`).

Out of scope:

- Vulnerabilities in third-party dependencies — please report those upstream.
- Findings in repositories that `sdlc-assessor` is invoked against. This tool reports on other repos' findings; it does not modify them.

## Hardening conventions in this repo

- Detectors must respect ignore directories (`.git`, `node_modules`, `.venv`, etc.) and never read files larger than 5 MB without explicit opt-in.
- Secrets scanning runs over text files only; binary content is detected via null-byte sniffing of the first 8 KB and skipped.
- The CLI never executes code from the assessed repository; only static analysis is performed.
