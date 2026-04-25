"""Hard blocker detection.

Implements ``docs/scoring_engine_spec.md §Step 5`` blocker rules.
"""

from __future__ import annotations

CREDENTIAL_FILE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
CREDENTIAL_FILE_NAMES = {"id_rsa", "id_dsa", "id_ed25519", "id_ecdsa"}


def _path_looks_like_credential(path: str) -> bool:
    lowered = path.lower()
    if any(lowered.endswith(suf) for suf in CREDENTIAL_FILE_SUFFIXES):
        return True
    name = path.rsplit("/", 1)[-1].lower()
    return name in CREDENTIAL_FILE_NAMES


def detect_hard_blockers(
    findings: list[dict],
    *,
    maturity_profile: dict | None = None,
    inventory: dict | None = None,
    classification: dict | None = None,
) -> list[dict]:
    """Identify hard blockers from findings + maturity policy + inventory.

    Rules implemented (per docs/scoring_engine_spec.md §Step 5):
    1. Probable secrets (any subcategory `probable_secrets`) → critical.
    2. Any finding with `severity == "critical"` → critical.
    3. Maturity profile flag `missing_ci_is_blocker` AND missing_ci finding → high.
    4. Maturity profile flag `missing_tests_and_missing_ci_can_trigger_blocker` AND
       missing_ci finding AND zero test files → critical.
    5. Unsafe command execution (`subprocess_shell_true`, `exec_usage`,
       `exec_sync_usage`) in a service+network_exposure repo → critical.
    6. Committed credential file (`*.pem`, `*.key`, `id_rsa`, etc.) → critical.
    """
    blockers: list[dict] = []
    maturity_profile = maturity_profile or {}
    inventory = inventory or {}
    classification = classification or {}

    test_files = int(inventory.get("test_files", 0))
    has_missing_ci = any(f.get("subcategory") == "missing_ci" for f in findings)

    seen_subcats: set[str] = set()
    for f in findings:
        subcat = f.get("subcategory", "")
        severity = f.get("severity", "")

        # Rule 1 + 2.
        if subcat == "probable_secrets" or severity == "critical":
            blockers.append(
                {
                    "title": f.get("statement", "Critical finding requires resolution."),
                    "reason": f.get("statement", ""),
                    "severity": "critical",
                    "evidence_refs": [f.get("id", "")],
                    "closure_requirements": [
                        "Rotate any exposed credentials.",
                        "Remove the offending value from git history (e.g. via `git filter-repo`).",
                    ] if subcat == "probable_secrets" else ["Resolve the underlying critical finding."],
                }
            )
            seen_subcats.add(subcat)

        # Rule 6: committed credential file.
        for ev in f.get("evidence", []) or []:
            path = ev.get("path", "")
            if path and _path_looks_like_credential(path):
                blockers.append(
                    {
                        "title": "Committed credential or private key detected.",
                        "reason": f"Credential-shaped file in repo: {path}",
                        "severity": "critical",
                        "evidence_refs": [f.get("id", "")],
                        "closure_requirements": [
                            "Remove the file from the working tree and git history.",
                            "Rotate the corresponding key/credential immediately.",
                        ],
                    }
                )
                break

    # Rule 3 + 4: missing CI / missing CI + tests under production maturity.
    if has_missing_ci:
        if maturity_profile.get("missing_tests_and_missing_ci_can_trigger_blocker") and test_files == 0:
            blockers.append(
                {
                    "title": "Missing tests and CI on production-profile repository.",
                    "reason": (
                        "Production-maturity profile requires CI and at least one test; both are absent."
                    ),
                    "severity": "critical",
                    "evidence_refs": [],
                    "closure_requirements": [
                        "Add a CI workflow (`.github/workflows/ci.yml`).",
                        "Add at least one automated test exercising the package's main entrypoint.",
                    ],
                }
            )
        elif maturity_profile.get("missing_ci_is_blocker"):
            blockers.append(
                {
                    "title": "Missing CI on production-maturity repository.",
                    "reason": "Production maturity requires automated CI gating.",
                    "severity": "high",
                    "evidence_refs": [],
                    "closure_requirements": [
                        "Add a CI workflow under `.github/workflows/`.",
                    ],
                }
            )

    # Rule 5: unsafe command execution in service + network_exposure.
    archetype = classification.get("repo_archetype")
    network_exposure = bool(classification.get("network_exposure", False))
    if archetype == "service" and network_exposure:
        for f in findings:
            if f.get("subcategory") in {"subprocess_shell_true", "exec_usage", "exec_sync_usage"}:
                blockers.append(
                    {
                        "title": "Unsafe command execution in network-facing service.",
                        "reason": f.get("statement", ""),
                        "severity": "critical",
                        "evidence_refs": [f.get("id", "")],
                        "closure_requirements": [
                            "Replace shell-based execution with argument-array invocation.",
                            "Validate or constrain any user-controlled input before subprocess use.",
                        ],
                    }
                )

    return blockers
