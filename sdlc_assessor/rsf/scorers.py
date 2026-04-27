"""Per-criterion scorers — map detector evidence to RSF v1.0 anchors.

Discipline (RSF §1, §3, §6):
- Score 0 only when *absence is observable* (e.g., no README, no LICENSE,
  no test files). "We didn't look" is **not** absence.
- Score `?` (UNVERIFIED) when the criterion needs evidence the current
  collector pipeline doesn't gather (e.g., line-coverage %, DORA
  metrics, branch-protection settings). The RSF deliberately separates
  absent from unverified so reports don't conflate them.
- Score `N/A` only when the criterion cannot apply to this asset
  (e.g., D8.* for an internal tool with no compliance scope).
- Every score carries an evidence trail (file path, finding id, etc.)
  and a one-sentence rationale citing the level anchor that matched.

Each scorer returns a :class:`CriterionScore`. The list of all scorers
is consumed by :func:`sdlc_assessor.rsf.score.assess_repository`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sdlc_assessor.rsf.aggregate import (
    NOT_APPLICABLE,
    UNVERIFIED,
    CriterionScore,
)

# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

# Conventional locations for governance / docs files (RSF §6 / §2 references).
_README_CANDIDATES = (
    "README.md", "Readme.md", "readme.md", "README",
    "README.rst", "README.txt", "docs/README.md", ".github/README.md",
)
_LICENSE_CANDIDATES = (
    "LICENSE", "LICENSE.md", "LICENSE.txt", "License", "license",
    "COPYING", "COPYING.md", ".github/LICENSE",
)
_SECURITY_CANDIDATES = (
    "SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md",
)
_CONTRIBUTING_CANDIDATES = (
    "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
)
_CODE_OF_CONDUCT_CANDIDATES = (
    "CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md",
    "docs/CODE_OF_CONDUCT.md",
)
_GOVERNANCE_CANDIDATES = (
    "GOVERNANCE.md", ".github/GOVERNANCE.md", "docs/GOVERNANCE.md",
)
_CODEOWNERS_CANDIDATES = (
    "CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS",
)


def _find_first(repo_path: Path, candidates: tuple[str, ...]) -> Path | None:
    """Return the first existing path among ``candidates``, or None."""
    for rel in candidates:
        p = repo_path / rel
        if p.is_file():
            return p
    return None


def _list_workflow_files(repo_path: Path) -> list[Path]:
    workflows_dir = repo_path / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    return [
        p for p in workflows_dir.iterdir()
        if p.is_file() and p.suffix in {".yml", ".yaml"}
    ]


def _read_text_safely(path: Path, *, max_bytes: int = 200_000) -> str:
    """Read text with a defensive size cap; returns empty on any error."""
    try:
        if path.stat().st_size > max_bytes:
            with path.open("rb") as f:
                return f.read(max_bytes).decode(errors="ignore")
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def _workflows_mention(repo_path: Path, *needles: str) -> list[Path]:
    """Workflow files whose text contains any of ``needles`` (case-insensitive)."""
    out: list[Path] = []
    needles_lc = tuple(n.lower() for n in needles)
    for wf in _list_workflow_files(repo_path):
        text = _read_text_safely(wf).lower()
        if not text:
            continue
        if any(n in text for n in needles_lc):
            out.append(wf)
    return out


# ---------------------------------------------------------------------------
# Finding helpers
# ---------------------------------------------------------------------------


def _findings(scored: dict) -> list[dict]:
    return list(scored.get("findings") or [])


def _findings_with_subcategory(scored: dict, *subcategories: str) -> list[dict]:
    targets = {s.lower() for s in subcategories}
    return [
        f for f in _findings(scored)
        if (f.get("subcategory") or "").lower() in targets
    ]


def _git_summary(scored: dict) -> dict:
    return (scored.get("repo_meta") or {}).get("git_summary") or {}


def _inventory(scored: dict) -> dict:
    return scored.get("inventory") or {}


# ---------------------------------------------------------------------------
# D1. Code Quality & Maintainability
# ---------------------------------------------------------------------------


def score_d1_1(scored: dict, repo_path: Path) -> CriterionScore:
    """D1.1 Automated test coverage."""
    inv = _inventory(scored)
    test_files = int(inv.get("test_files", 0) or 0)
    workflow_files = int(inv.get("workflow_files", 0) or 0)

    if test_files == 0:
        return CriterionScore(
            criterion_id="D1.1",
            value=0,
            evidence=[f"inventory.test_files={test_files}"],
            rationale="No automated tests in the repo.",
        )
    if workflow_files == 0:
        return CriterionScore(
            criterion_id="D1.1",
            value=1,
            evidence=[
                f"inventory.test_files={test_files}",
                f"inventory.workflow_files={workflow_files}",
            ],
            rationale="Tests exist; not run in CI; coverage unmeasured.",
        )
    return CriterionScore(
        criterion_id="D1.1",
        value=UNVERIFIED,
        evidence=[
            f"inventory.test_files={test_files}",
            f"inventory.workflow_files={workflow_files}",
        ],
        rationale=(
            "Tests run in CI but line-coverage % is not collected by this "
            "assessor. RSF levels 2–5 require coverage measurement; "
            "score is unverified."
        ),
    )


_SAST_LINTER_NEEDLES = (
    "ruff", "eslint", "codeql", "semgrep", "bandit", "mypy", "pylint",
    "tflint", "shellcheck", "pyflakes", "tslint", "checkov", "trivy",
)


def score_d1_2(scored: dict, repo_path: Path) -> CriterionScore:
    """D1.2 Static analysis & lint discipline."""
    workflows = _list_workflow_files(repo_path)
    if not workflows:
        return CriterionScore(
            criterion_id="D1.2",
            value=0,
            evidence=["no .github/workflows/*.yml files"],
            rationale="No SAST or linter in CI.",
        )
    sast_workflows = _workflows_mention(repo_path, *_SAST_LINTER_NEEDLES)
    if not sast_workflows:
        return CriterionScore(
            criterion_id="D1.2",
            value=0,
            evidence=[f"{len(workflows)} workflow file(s); no SAST/lint references"],
            rationale="No SAST or linter in CI.",
        )
    return CriterionScore(
        criterion_id="D1.2",
        value=UNVERIFIED,
        evidence=[f"workflows referencing SAST/lint: {[p.name for p in sast_workflows]}"],
        rationale=(
            "SAST/lint configured in CI, but whether findings block merges "
            "(level 3+) or are tuned with custom rules (level 4+) is not "
            "observable from a static snapshot."
        ),
    )


def score_d1_3(scored: dict, repo_path: Path) -> CriterionScore:
    """D1.3 Code complexity / hotspot management."""
    return CriterionScore(
        criterion_id="D1.3",
        value=UNVERIFIED,
        evidence=[],
        rationale=(
            "Complexity / hotspot tracking is not measured by this assessor. "
            "Requires behavioral-code-analysis tooling (e.g. CodeScene)."
        ),
    )


# ---------------------------------------------------------------------------
# D2. Application Security Posture
# ---------------------------------------------------------------------------


def score_d2_1(scored: dict, repo_path: Path) -> CriterionScore:
    """D2.1 Known vulnerabilities in dependencies (CVE/OSV)."""
    has_dependabot = (repo_path / ".github" / "dependabot.yml").is_file() or (
        repo_path / ".github" / "dependabot.yaml"
    ).is_file()
    has_renovate = any(
        (repo_path / candidate).is_file()
        for candidate in ("renovate.json", "renovate.json5", ".renovaterc", ".renovaterc.json")
    )
    osv_workflows = _workflows_mention(repo_path, "osv-scanner", "osv-scan", "trivy", "snyk")

    evidence: list[str] = []
    if has_dependabot:
        evidence.append(".github/dependabot.yml present")
    if has_renovate:
        evidence.append("Renovate config present")
    if osv_workflows:
        evidence.append(f"vuln-scan workflow(s): {[p.name for p in osv_workflows]}")

    if has_dependabot or has_renovate or osv_workflows:
        return CriterionScore(
            criterion_id="D2.1",
            value=UNVERIFIED,
            evidence=evidence,
            rationale=(
                "Dependency-update / vuln-scan tooling configured. Resolved-vs-"
                "open SLA timing (RSF levels 1–3) and reachability analysis "
                "(level 4) require CVE-feed data this assessor does not collect."
            ),
        )
    # No scanning detected; we can't claim level 0 ("≥1 critical CVE open >30 days; no scanning")
    # without actually running an OSV scan. Mark unverified.
    return CriterionScore(
        criterion_id="D2.1",
        value=UNVERIFIED,
        evidence=["no dependency-update / vuln-scan config detected"],
        rationale=(
            "No Dependabot / Renovate / OSV-Scanner configuration detected, but "
            "this assessor does not run an OSV scan to determine whether "
            "critical CVEs are open. Level 0 requires affirmative evidence of "
            "open critical CVEs; score is unverified."
        ),
    )


def score_d2_2(scored: dict, repo_path: Path) -> CriterionScore:
    """D2.2 Secrets in source / git history."""
    secret_findings = _findings_with_subcategory(scored, "probable_secrets", "committed_credential")
    has_gitleaks_config = any(
        (repo_path / p).is_file()
        for p in (".gitleaks.toml", ".gitleaks.yaml", ".github/gitleaks.toml")
    )
    secret_scan_workflows = _workflows_mention(
        repo_path, "gitleaks", "trufflehog", "secret-scanning", "ggshield",
    )
    evidence: list[str] = []
    if secret_findings:
        evidence.append(f"{len(secret_findings)} probable-secret finding(s)")
    if has_gitleaks_config:
        evidence.append(".gitleaks.toml present")
    if secret_scan_workflows:
        evidence.append(f"secret-scan workflow(s): {[p.name for p in secret_scan_workflows]}")

    if secret_findings and not (has_gitleaks_config or secret_scan_workflows):
        return CriterionScore(
            criterion_id="D2.2",
            value=0,
            evidence=evidence,
            rationale="Active secrets discoverable; no scanning config detected.",
        )
    if secret_findings and (has_gitleaks_config or secret_scan_workflows):
        return CriterionScore(
            criterion_id="D2.2",
            value=1,
            evidence=evidence,
            rationale=(
                "Secret-scanning configured but historical secrets present "
                "(scanning detected unrotated material)."
            ),
        )
    if not secret_findings and (has_gitleaks_config or secret_scan_workflows):
        return CriterionScore(
            criterion_id="D2.2",
            value=UNVERIFIED,
            evidence=evidence,
            rationale=(
                "Secret-scanning configured and no findings present, but "
                "vault adoption / OIDC / rotation cadence (RSF levels 3–5) "
                "are not observable from the repo alone."
            ),
        )
    return CriterionScore(
        criterion_id="D2.2",
        value=UNVERIFIED,
        evidence=["no probable-secret findings; no secret-scanning config"],
        rationale=(
            "No secrets findings emitted by this assessor's detector and no "
            "secret-scanning tool detected. RSF level 0 requires affirmative "
            "evidence of active secrets; level 2+ requires evidence of "
            "scanning. Score unverified."
        ),
    )


_TOP_TEN_PATTERN_SUBCATS = (
    "probable_secrets", "committed_credential", "subprocess_shell_true",
    "exec_call", "execsync", "unsafe_sql_string", "eval_or_exec",
    "pickle_load_untrusted", "os_system_call", "requests_verify_false",
)


def score_d2_3(scored: dict, repo_path: Path) -> CriterionScore:
    """D2.3 ASVS / Top 10 conformance."""
    top_ten_findings = _findings_with_subcategory(scored, *_TOP_TEN_PATTERN_SUBCATS)
    if top_ten_findings:
        # RSF level 0 anchor: "common Top 10 patterns visible (hardcoded creds, raw SQL)".
        return CriterionScore(
            criterion_id="D2.3",
            value=0,
            evidence=[
                f"{len(top_ten_findings)} OWASP Top 10 / CWE Top 25 pattern(s) "
                "detected"
            ]
            + [f"{f.get('id')}={f.get('subcategory')}" for f in top_ten_findings[:3]],
            rationale=(
                "Common OWASP Top 10 / CWE Top 25 patterns present (hardcoded "
                "credentials, OS command injection, etc.). RSF level 0."
            ),
        )
    return CriterionScore(
        criterion_id="D2.3",
        value=UNVERIFIED,
        evidence=[],
        rationale=(
            "No Top 10 pattern findings emitted, but ASVS-level conformance "
            "(RSF levels 2–5) requires a declared ASVS target and a structured "
            "review this assessor does not perform."
        ),
    )


def score_d2_4(scored: dict, repo_path: Path) -> CriterionScore:
    """D2.4 Branch protection & code review enforcement."""
    has_codeowners = _find_first(repo_path, _CODEOWNERS_CANDIDATES) is not None
    if has_codeowners:
        return CriterionScore(
            criterion_id="D2.4",
            value=UNVERIFIED,
            evidence=["CODEOWNERS file present"],
            rationale=(
                "CODEOWNERS present (RSF level 3 minimum). Branch-protection "
                "rule enforcement, signed-commit requirements, and admin-bypass "
                "policy are not observable without the GitHub Settings API."
            ),
        )
    return CriterionScore(
        criterion_id="D2.4",
        value=UNVERIFIED,
        evidence=["no CODEOWNERS file"],
        rationale=(
            "CODEOWNERS absent. Branch-protection settings are not observable "
            "from the repo alone (require the GitHub Settings API). Score "
            "unverified."
        ),
    )


# ---------------------------------------------------------------------------
# D3. Supply Chain Integrity
# ---------------------------------------------------------------------------


_SBOM_FILENAMES = (
    "sbom.json", "sbom.cdx.json", "sbom.spdx.json", "sbom.cyclonedx.json",
    "bom.json", "sbom.xml", "sbom.cdx.xml", "sbom.spdx",
)


def score_d3_1(scored: dict, repo_path: Path) -> CriterionScore:
    """D3.1 SBOM availability."""
    sbom_files = [
        repo_path / name for name in _SBOM_FILENAMES if (repo_path / name).is_file()
    ]
    sbom_workflows = _workflows_mention(
        repo_path, "syft", "cyclonedx", "spdx", "anchore/sbom-action",
    )
    if sbom_files or sbom_workflows:
        evidence: list[str] = []
        if sbom_files:
            evidence.append(f"SBOM file(s): {[p.name for p in sbom_files]}")
        if sbom_workflows:
            evidence.append(f"SBOM workflow(s): {[p.name for p in sbom_workflows]}")
        return CriterionScore(
            criterion_id="D3.1",
            value=UNVERIFIED,
            evidence=evidence,
            rationale=(
                "SBOM tooling detected. Distinguishing per-release vs per-build "
                "publication, signing, and VEX adoption (RSF levels 2–5) "
                "requires release-channel inspection this assessor does not do."
            ),
        )
    return CriterionScore(
        criterion_id="D3.1",
        value=0,
        evidence=["no SBOM files; no SBOM workflows"],
        rationale="No SBOM produced.",
    )


def score_d3_2(scored: dict, repo_path: Path) -> CriterionScore:
    """D3.2 Artifact signing."""
    signing_workflows = _workflows_mention(
        repo_path, "cosign", "sigstore", "in-toto", "slsa-framework",
    )
    if signing_workflows:
        return CriterionScore(
            criterion_id="D3.2",
            value=UNVERIFIED,
            evidence=[f"signing workflow(s): {[p.name for p in signing_workflows]}"],
            rationale=(
                "Sigstore / cosign / in-toto referenced in workflows. Whether "
                "signing is keyless (level 3) or paired with admission-control "
                "policy (level 5) requires release-channel + deployment "
                "inspection."
            ),
        )
    return CriterionScore(
        criterion_id="D3.2",
        value=0,
        evidence=["no signing workflow references"],
        rationale="No artifact signing detected.",
    )


def score_d3_3(scored: dict, repo_path: Path) -> CriterionScore:
    """D3.3 SLSA build track level."""
    workflows = _list_workflow_files(repo_path)
    if not workflows:
        return CriterionScore(
            criterion_id="D3.3",
            value=0,
            evidence=["no .github/workflows/*.yml files"],
            rationale="SLSA L0 — builds on developer machines (no hosted CI detected).",
        )
    slsa_workflows = _workflows_mention(repo_path, "slsa-framework", "slsa-generator", "in-toto")
    evidence = [f"{len(workflows)} workflow file(s)"]
    if slsa_workflows:
        evidence.append(f"SLSA-related: {[p.name for p in slsa_workflows]}")
        return CriterionScore(
            criterion_id="D3.3",
            value=UNVERIFIED,
            evidence=evidence,
            rationale=(
                "SLSA framework actions referenced. Whether the build platform "
                "actually emits and signs provenance (L1+) and whether it's a "
                "hardened, tamper-resistant builder (L3+) requires runtime "
                "attestation inspection."
            ),
        )
    return CriterionScore(
        criterion_id="D3.3",
        value=UNVERIFIED,
        evidence=evidence,
        rationale=(
            "Hosted CI workflows present (potential SLSA L1+) but no explicit "
            "SLSA-framework or provenance-generation actions detected. SLSA "
            "level cannot be asserted from workflow presence alone."
        ),
    )


def score_d3_4(scored: dict, repo_path: Path) -> CriterionScore:
    """D3.4 Dependency-update automation."""
    has_dependabot = (repo_path / ".github" / "dependabot.yml").is_file() or (
        repo_path / ".github" / "dependabot.yaml"
    ).is_file()
    has_renovate = any(
        (repo_path / p).is_file()
        for p in ("renovate.json", "renovate.json5", ".renovaterc", ".renovaterc.json")
    )
    if has_dependabot or has_renovate:
        return CriterionScore(
            criterion_id="D3.4",
            value=2,
            evidence=[
                ".github/dependabot.yml" if has_dependabot else "Renovate config",
            ],
            rationale=(
                "Dependabot or Renovate configured. RSF level 2: configured for "
                "security updates. Distinguishing higher levels (minor + major "
                "auto-update, reachability-aware prioritization) requires "
                "scope inspection of the config file."
            ),
        )
    return CriterionScore(
        criterion_id="D3.4",
        value=0,
        evidence=["no Dependabot / Renovate config"],
        rationale="No automated dependency-update tooling detected.",
    )


# ---------------------------------------------------------------------------
# D4. Delivery Performance (DORA)
#
# All four DORA metrics require continuous-deployment evidence (deploy
# events, lead times, CFR, MTTR) that this assessor does not currently
# capture. Per the discipline rule, all four are `?`.
# ---------------------------------------------------------------------------


def _dora_unverified(criterion_id: str, what: str) -> CriterionScore:
    return CriterionScore(
        criterion_id=criterion_id,
        value=UNVERIFIED,
        evidence=[],
        rationale=(
            f"DORA {what} requires continuous-deployment event history "
            "(deploy events, PR-to-deploy lead time, rollback-rate, MTTR) "
            "that this assessor does not collect. See "
            "docs/frameworks/dora.md for the gap analysis."
        ),
    )


def score_d4_1(scored: dict, repo_path: Path) -> CriterionScore:
    return _dora_unverified("D4.1", "deployment frequency")


def score_d4_2(scored: dict, repo_path: Path) -> CriterionScore:
    return _dora_unverified("D4.2", "lead time for changes")


def score_d4_3(scored: dict, repo_path: Path) -> CriterionScore:
    return _dora_unverified("D4.3", "change failure rate")


def score_d4_4(scored: dict, repo_path: Path) -> CriterionScore:
    return _dora_unverified("D4.4", "failed-deployment recovery time")


# ---------------------------------------------------------------------------
# D5. Engineering Discipline
# ---------------------------------------------------------------------------


def score_d5_1(scored: dict, repo_path: Path) -> CriterionScore:
    """D5.1 PR review depth."""
    has_codeowners = _find_first(repo_path, _CODEOWNERS_CANDIDATES) is not None
    if has_codeowners:
        return CriterionScore(
            criterion_id="D5.1",
            value=UNVERIFIED,
            evidence=["CODEOWNERS file present"],
            rationale=(
                "CODEOWNERS present (RSF level 3 minimum). Review depth, "
                "comment density, and rework metrics (levels 3–5) require "
                "PR-history analysis this assessor does not perform."
            ),
        )
    return CriterionScore(
        criterion_id="D5.1",
        value=UNVERIFIED,
        evidence=["no CODEOWNERS"],
        rationale=(
            "CODEOWNERS absent. PR review depth cannot be measured from a "
            "static snapshot (requires GitHub PR-history)."
        ),
    )


def score_d5_2(scored: dict, repo_path: Path) -> CriterionScore:
    """D5.2 CI health (green rate, time, flakiness)."""
    workflows = _list_workflow_files(repo_path)
    if not workflows:
        return CriterionScore(
            criterion_id="D5.2",
            value=0,
            evidence=["no .github/workflows/*.yml files"],
            rationale="No CI configured.",
        )
    return CriterionScore(
        criterion_id="D5.2",
        value=UNVERIFIED,
        evidence=[f"{len(workflows)} workflow file(s)"],
        rationale=(
            "CI workflows present. Green rate, build times, and flakiness "
            "(levels 1–5) require workflow-run history this assessor does "
            "not collect."
        ),
    )


def score_d5_3(scored: dict, repo_path: Path) -> CriterionScore:
    """D5.3 Branch hygiene."""
    return CriterionScore(
        criterion_id="D5.3",
        value=UNVERIFIED,
        evidence=[],
        rationale=(
            "Branch hygiene (trunk-based vs long-lived branches, linear-history "
            "enforcement, conventional commits) requires git-history walking "
            "and merge-policy inspection this assessor does not currently do."
        ),
    )


def score_d5_4(scored: dict, repo_path: Path) -> CriterionScore:
    """D5.4 Release cadence and tagging.

    RSF anchors:
      0: No releases or untagged releases.
      1: Releases tagged but irregular; no notes.
      2: SemVer tagging; release notes manual.
      3: SemVer + automated release notes; release branches as needed.
      4: Release-please / changesets / semantic-release automation.
      5: Above + release attestations (SLSA provenance attached).
    """
    inv = _inventory(scored)
    git = _git_summary(scored)
    tag_count = int(inv.get("tag_count") or git.get("tag_count") or 0)
    release_count = int(inv.get("release_count") or git.get("release_count") or 0)

    if tag_count == 0 and release_count == 0:
        return CriterionScore(
            criterion_id="D5.4",
            value=0,
            evidence=[f"tag_count={tag_count}", f"release_count={release_count}"],
            rationale="No releases or untagged releases (RSF D5.4 level 0).",
        )

    has_release_automation = bool(_workflows_mention(
        repo_path, "release-please", "semantic-release", "changesets",
    ))
    has_slsa_provenance = bool(_workflows_mention(
        repo_path, "slsa-framework", "slsa-generator",
    ))
    evidence = [f"tag_count={tag_count}", f"release_count={release_count}"]
    if has_release_automation:
        evidence.append("release-automation workflow detected")
    if has_slsa_provenance:
        evidence.append("SLSA provenance workflow detected")

    # Level 4: release automation present.
    if has_release_automation and has_slsa_provenance:
        return CriterionScore(
            criterion_id="D5.4",
            value=5,
            evidence=evidence,
            rationale=(
                "Release automation + SLSA provenance attestations "
                "(RSF D5.4 level 5)."
            ),
        )
    if has_release_automation:
        return CriterionScore(
            criterion_id="D5.4",
            value=4,
            evidence=evidence,
            rationale=(
                "Release-please / semantic-release / changesets automation "
                "detected (RSF D5.4 level 4)."
            ),
        )

    # Without automation but with multiple tags, score 1 ("tagged but irregular").
    # Distinguishing level 2+ (SemVer adherence + release notes) requires
    # content analysis we don't do — return level 1 conservatively.
    if tag_count >= 1:
        return CriterionScore(
            criterion_id="D5.4",
            value=1,
            evidence=evidence,
            rationale=(
                f"{tag_count} tag(s) present; releases tagged but no automation "
                "detected. SemVer adherence + release-note structure (levels "
                "2–3) require content analysis. RSF D5.4 level 1."
            ),
        )

    return CriterionScore(
        criterion_id="D5.4",
        value=UNVERIFIED,
        evidence=evidence,
        rationale="tag_count and release_count both unknown.",
    )


# ---------------------------------------------------------------------------
# D6. Documentation & Transparency
# ---------------------------------------------------------------------------


def score_d6_1(scored: dict, repo_path: Path) -> CriterionScore:
    """D6.1 README and onboarding."""
    readme = _find_first(repo_path, _README_CANDIDATES)
    if readme is None:
        return CriterionScore(
            criterion_id="D6.1",
            value=0,
            evidence=["no README found"],
            rationale="No README or stub README.",
        )
    text = _read_text_safely(readme)
    line_count = len([line for line in text.splitlines() if line.strip()])
    if line_count < 5:
        return CriterionScore(
            criterion_id="D6.1",
            value=0,
            evidence=[f"{readme.name}: {line_count} non-empty line(s)"],
            rationale="Stub README (fewer than 5 non-empty lines).",
        )
    return CriterionScore(
        criterion_id="D6.1",
        value=UNVERIFIED,
        evidence=[f"{readme.name}: {line_count} non-empty line(s)"],
        rationale=(
            "README present and non-trivial. Whether setup instructions are "
            "complete (level 2), architecture is documented (level 3), ADRs "
            "are published (level 4), or runbook + threat model exist (level 5) "
            "requires content analysis this assessor does not perform."
        ),
    )


_SPDX_LICENSE_HINTS = (
    "MIT License", "Apache License", "BSD ", "Mozilla Public License",
    "GPL ", "LGPL ", "GNU General Public", "ISC License", "Unlicense",
    "Creative Commons", "SPDX-License-Identifier",
)


def score_d6_2(scored: dict, repo_path: Path) -> CriterionScore:
    """D6.2 License clarity."""
    license_file = _find_first(repo_path, _LICENSE_CANDIDATES)
    if license_file is None:
        readme = _find_first(repo_path, _README_CANDIDATES)
        if readme is not None and any(
            hint in _read_text_safely(readme) for hint in _SPDX_LICENSE_HINTS
        ):
            return CriterionScore(
                criterion_id="D6.2",
                value=1,
                evidence=[f"{readme.name} mentions a license; no LICENSE file"],
                rationale="License declared in README only; no LICENSE file.",
            )
        return CriterionScore(
            criterion_id="D6.2",
            value=0,
            evidence=["no LICENSE file"],
            rationale="No LICENSE file.",
        )
    text = _read_text_safely(license_file)
    if any(hint in text for hint in _SPDX_LICENSE_HINTS):
        return CriterionScore(
            criterion_id="D6.2",
            value=2,
            evidence=[f"{license_file.name}: matches SPDX hint"],
            rationale="LICENSE file matches an SPDX identifier.",
        )
    return CriterionScore(
        criterion_id="D6.2",
        value=2,
        evidence=[f"{license_file.name}: present (no SPDX hint detected)"],
        rationale=(
            "LICENSE file present; SPDX identifier match not verified. RSF "
            "level 2 minimum."
        ),
    )


def score_d6_3(scored: dict, repo_path: Path) -> CriterionScore:
    """D6.3 Security policy & disclosure."""
    sec = _find_first(repo_path, _SECURITY_CANDIDATES)
    if sec is None:
        return CriterionScore(
            criterion_id="D6.3",
            value=0,
            evidence=["no SECURITY.md"],
            rationale="No SECURITY.md.",
        )
    text = _read_text_safely(sec)
    has_contact = any(
        hint in text.lower()
        for hint in ("@", "email", "report", "disclosure", "contact")
    )
    line_count = len([line for line in text.splitlines() if line.strip()])
    if line_count < 5:
        return CriterionScore(
            criterion_id="D6.3",
            value=1,
            evidence=[f"{sec.name}: {line_count} non-empty line(s)"],
            rationale="SECURITY.md present but vague.",
        )
    if has_contact:
        return CriterionScore(
            criterion_id="D6.3",
            value=2,
            evidence=[f"{sec.name}: contact / disclosure language present"],
            rationale="SECURITY.md names a contact; disclosure process defined.",
        )
    return CriterionScore(
        criterion_id="D6.3",
        value=1,
        evidence=[f"{sec.name}: no contact / disclosure language detected"],
        rationale="SECURITY.md present but vague (no contact / disclosure language).",
    )


def score_d6_4(scored: dict, repo_path: Path) -> CriterionScore:
    """D6.4 Contribution guidance & governance."""
    contributing = _find_first(repo_path, _CONTRIBUTING_CANDIDATES)
    if contributing is None:
        return CriterionScore(
            criterion_id="D6.4",
            value=0,
            evidence=["no CONTRIBUTING.md"],
            rationale="No CONTRIBUTING.md, no governance.",
        )
    coc = _find_first(repo_path, _CODE_OF_CONDUCT_CANDIDATES)
    governance = _find_first(repo_path, _GOVERNANCE_CANDIDATES)
    if governance is not None:
        return CriterionScore(
            criterion_id="D6.4",
            value=3,
            evidence=[
                f"{contributing.name} present",
                f"{governance.name} present",
                f"{coc.name} present" if coc else "no CODE_OF_CONDUCT",
            ],
            rationale=(
                "CONTRIBUTING + GOVERNANCE present (RSF level 3 minimum). "
                "Roadmap + open governance (levels 4–5) require additional "
                "content analysis."
            ),
        )
    if coc is not None:
        return CriterionScore(
            criterion_id="D6.4",
            value=2,
            evidence=[f"{contributing.name} present", f"{coc.name} present"],
            rationale="CONTRIBUTING + Code of Conduct present (no GOVERNANCE.md).",
        )
    return CriterionScore(
        criterion_id="D6.4",
        value=1,
        evidence=[f"{contributing.name} present"],
        rationale="CONTRIBUTING.md present.",
    )


# ---------------------------------------------------------------------------
# D7. Sustainability & Team Health
# ---------------------------------------------------------------------------


def score_d7_1(scored: dict, repo_path: Path) -> CriterionScore:
    """D7.1 Bus factor / knowledge concentration.

    RSF v1.0 D7.1 anchors are *literally* about author share — level 0
    is "Single contributor authored >80% of code; no co-maintainers."
    Read ``top_authors`` directly (most precise signal); fall back to
    ``bus_factor`` only when top_authors isn't available.
    """
    git = _git_summary(scored)
    top_authors = git.get("top_authors") or []
    has_codeowners = _find_first(repo_path, _CODEOWNERS_CANDIDATES) is not None

    # Derive a top-author share if available — most precise per the RSF anchors.
    leading_share: float | None = None
    if top_authors and isinstance(top_authors, list):
        first = top_authors[0]
        if isinstance(first, dict):
            try:
                leading_share = float(first.get("share", 0.0))
            except (TypeError, ValueError):
                leading_share = None

    contributor_count = len(top_authors) if top_authors else 0
    bus = git.get("estimated_bus_factor") or git.get("bus_factor")
    try:
        bus_n = int(float(bus)) if bus is not None else 0
    except (TypeError, ValueError):
        bus_n = 0

    evidence = []
    if leading_share is not None:
        evidence.append(f"top_author_share={leading_share:.2f}")
    if top_authors:
        evidence.append(f"contributors_observed={contributor_count}")
    evidence.append(f"bus_factor={bus_n}")
    if has_codeowners:
        evidence.append("CODEOWNERS present")

    # No data at all → unverified.
    if leading_share is None and bus_n == 0 and contributor_count == 0:
        return CriterionScore(
            criterion_id="D7.1",
            value=UNVERIFIED,
            evidence=[],
            rationale="git_summary did not report contributor data.",
        )

    # RSF level 0 — *exact* anchor match: "Single contributor authored >80% of code".
    if leading_share is not None and leading_share > 0.80:
        return CriterionScore(
            criterion_id="D7.1",
            value=0,
            evidence=evidence,
            rationale=(
                f"Single contributor authored {leading_share:.0%} of analyzed "
                f"commits (>80% threshold); no co-maintainers (RSF D7.1 level 0)."
            ),
        )

    # RSF level 1: "2 contributors share most work; high concentration."
    # Match either by bus_factor or by top-2 share dominance.
    if bus_n == 2 or (contributor_count == 2):
        return CriterionScore(
            criterion_id="D7.1",
            value=1,
            evidence=evidence,
            rationale=(
                "2 contributors share most work; high concentration in "
                "critical paths (RSF D7.1 level 1)."
            ),
        )

    # RSF level 2: "3+ active contributors; some critical paths still single-owner."
    if bus_n >= 3 and bus_n <= 4 or contributor_count in (3, 4):
        return CriterionScore(
            criterion_id="D7.1",
            value=2,
            evidence=evidence,
            rationale=(
                "3+ active contributors; some critical paths still "
                "single-owner (RSF D7.1 level 2)."
            ),
        )

    # RSF level 3: "5+ active contributors; CODEOWNERS includes ≥2 reviewers per critical path."
    if (bus_n >= 5 or contributor_count >= 5) and has_codeowners:
        return CriterionScore(
            criterion_id="D7.1",
            value=3,
            evidence=evidence,
            rationale=(
                "5+ active contributors with CODEOWNERS in place "
                "(RSF D7.1 level 3)."
            ),
        )

    # 5+ contributors without CODEOWNERS doesn't quite hit level 3; cap at 2.
    if bus_n >= 5 or contributor_count >= 5:
        return CriterionScore(
            criterion_id="D7.1",
            value=2,
            evidence=evidence,
            rationale=(
                "5+ active contributors but no CODEOWNERS — caps at "
                "RSF D7.1 level 2 (no review-routing structure)."
            ),
        )

    # Single-contributor fallback.
    return CriterionScore(
        criterion_id="D7.1",
        value=0,
        evidence=evidence,
        rationale=(
            "Insufficient contributor breadth for any level above 0 "
            "(RSF D7.1 level 0)."
        ),
    )


def score_d7_2(scored: dict, repo_path: Path) -> CriterionScore:
    """D7.2 Activity (sustained, not spiky).

    RSF anchors:
      0: No commits in 6+ months.
      1: Commits clustered; long quiet periods.
      2: Commits roughly weekly.
      3: Commits multiple times per week with trailing-90-day stability.
      4: Sustained 12-month activity; no >2-week quiet windows.
      5: Sustained activity with diverse contributor base.

    We map: 30d / 90d / 180d / 365d commit counts to weekly cadence
    (commits/week ≈ commits_90d / 13), plus contributor diversity from
    top_authors length.
    """
    git = _git_summary(scored)
    commits_30d = git.get("commits_last_30_days")
    commits_90d = git.get("commits_last_90_days")
    commits_180d = git.get("commits_last_180_days")
    commits_365d = git.get("commits_last_365_days")
    top_authors = git.get("top_authors") or []
    contributor_count = len(top_authors) if isinstance(top_authors, list) else 0

    if all(v is None for v in (commits_30d, commits_90d, commits_180d, commits_365d)):
        return CriterionScore(
            criterion_id="D7.2",
            value=UNVERIFIED,
            evidence=[],
            rationale="git_summary did not report commit cadence.",
        )

    c30 = int(commits_30d or 0)
    c90 = int(commits_90d or 0)
    c180 = int(commits_180d or 0)
    c365 = int(commits_365d or 0)

    # Approximate weekly cadence over the last 90 days.
    weekly_90d = c90 / 13.0  # 13 weeks ≈ 90 days.

    evidence = [
        f"commits_last_30d={c30}",
        f"commits_last_90d={c90}",
        f"commits_last_180d={c180}",
        f"commits_last_365d={c365}",
        f"approx_commits_per_week_90d={weekly_90d:.1f}",
        f"contributor_count_observed={contributor_count}",
    ]

    # Level 0: No commits in 6+ months (RSF anchor verbatim).
    if c180 == 0:
        return CriterionScore(
            criterion_id="D7.2",
            value=0,
            evidence=evidence,
            rationale="No commits in 6+ months (RSF D7.2 level 0).",
        )

    # Level 5: sustained activity + diverse contributor base.
    if c365 >= 200 and weekly_90d >= 5 and contributor_count >= 5:
        return CriterionScore(
            criterion_id="D7.2",
            value=5,
            evidence=evidence,
            rationale=(
                "Sustained activity (≥200 commits/year, weekly cadence ≥5) "
                "with diverse contributor base (5+) — RSF D7.2 level 5."
            ),
        )

    # Level 4: sustained 12-month activity, no big quiet windows.
    # Approximate "no >2-week quiet windows" as commits in 30d AND 90d AND 180d AND 365d.
    if c30 >= 4 and c90 >= 13 and c180 >= 26 and c365 >= 52:
        return CriterionScore(
            criterion_id="D7.2",
            value=4,
            evidence=evidence,
            rationale=(
                "Sustained 12-month activity, no >2-week quiet windows "
                "(weekly+ cadence sustained over 365d). RSF D7.2 level 4."
            ),
        )

    # Level 3: multiple commits per week + 90d stability.
    if weekly_90d >= 3 and c30 >= 6:
        return CriterionScore(
            criterion_id="D7.2",
            value=3,
            evidence=evidence,
            rationale=(
                f"Multiple commits per week ({weekly_90d:.1f}/week over 90d) "
                "with trailing-90-day stability. RSF D7.2 level 3."
            ),
        )

    # Level 2: roughly weekly cadence (≥1/week over 90d).
    if weekly_90d >= 1:
        return CriterionScore(
            criterion_id="D7.2",
            value=2,
            evidence=evidence,
            rationale=(
                f"Commits roughly weekly ({weekly_90d:.1f}/week over 90d). "
                "RSF D7.2 level 2."
            ),
        )

    # Level 1: clustered with long quiet periods (some activity, but not weekly).
    return CriterionScore(
        criterion_id="D7.2",
        value=1,
        evidence=evidence,
        rationale=(
            f"Commits clustered ({c180} commits in 180d but only {c30} in 30d); "
            "long quiet periods. RSF D7.2 level 1."
        ),
    )


def score_d7_3(scored: dict, repo_path: Path) -> CriterionScore:
    """D7.3 Issue and PR responsiveness."""
    return CriterionScore(
        criterion_id="D7.3",
        value=UNVERIFIED,
        evidence=[],
        rationale=(
            "Issue / PR responsiveness requires GitHub Issues + PR history "
            "(triage time, cycle time, abandonment rate) this assessor does "
            "not currently collect."
        ),
    )


def score_d7_4(scored: dict, repo_path: Path) -> CriterionScore:
    """D7.4 Maintainer continuity."""
    git = _git_summary(scored)
    # Read top_authors directly (the precise signal) before falling back to
    # the legacy contributor_count keys that no current collector emits.
    top_authors = git.get("top_authors") or []
    contributors_n = len(top_authors) if isinstance(top_authors, list) else 0
    if contributors_n == 0:
        legacy = (
            git.get("contributor_count")
            or git.get("unique_authors")
            or git.get("active_contributors")
        )
        try:
            contributors_n = int(legacy) if legacy is not None else 0
        except (TypeError, ValueError):
            contributors_n = 0
    governance = _find_first(repo_path, _GOVERNANCE_CANDIDATES)
    codeowners = _find_first(repo_path, _CODEOWNERS_CANDIDATES)

    evidence = [f"contributors={contributors_n}"]
    if governance:
        evidence.append(f"{governance.name} present")
    if codeowners:
        evidence.append(f"{codeowners.name} present")

    if contributors_n == 0:
        return CriterionScore(
            criterion_id="D7.4",
            value=0,
            evidence=evidence,
            rationale="No contributors detected.",
        )
    if contributors_n == 1:
        return CriterionScore(
            criterion_id="D7.4",
            value=1,
            evidence=evidence,
            rationale="Single active maintainer; no documented succession.",
        )
    if contributors_n >= 2 and governance is not None:
        return CriterionScore(
            criterion_id="D7.4",
            value=3,
            evidence=evidence,
            rationale="≥2 active maintainers; written governance present.",
        )
    if contributors_n >= 2:
        return CriterionScore(
            criterion_id="D7.4",
            value=2,
            evidence=evidence,
            rationale="≥2 active maintainers; succession informal.",
        )
    return CriterionScore(
        criterion_id="D7.4",
        value=UNVERIFIED,
        evidence=evidence,
        rationale="Contributor count signal too noisy to score.",
    )


# ---------------------------------------------------------------------------
# D8. Compliance & Governance Posture (org-scoped)
#
# Per RSF §1: D8 sub-criteria are org-scoped. This assessor cannot score
# them from the repo alone; they remain `?` unless org evidence is supplied
# via a future CLI flag (e.g., --compliance-evidence). Marking them N/A
# would be incorrect — the criteria DO apply, they're just unverified.
# ---------------------------------------------------------------------------


def _compliance_unverified(criterion_id: str, what: str) -> CriterionScore:
    return CriterionScore(
        criterion_id=criterion_id,
        value=UNVERIFIED,
        evidence=[],
        rationale=(
            f"{what} requires org-scoped evidence (audit certificates, "
            "questionnaires, attestations) not collectable from the repo. "
            "Mark explicitly as N/A via --d8-not-applicable when the asset "
            "is genuinely out of compliance scope."
        ),
    )


def score_d8_1(scored: dict, repo_path: Path) -> CriterionScore:
    return _compliance_unverified("D8.1", "Secure SDLC framework conformance")


def score_d8_2(scored: dict, repo_path: Path) -> CriterionScore:
    return _compliance_unverified("D8.2", "Audit attestation (ISO 27001 / SOC 2)")


def score_d8_3(scored: dict, repo_path: Path) -> CriterionScore:
    return _compliance_unverified("D8.3", "Sectoral regulatory conformance")


def score_d8_4(scored: dict, repo_path: Path) -> CriterionScore:
    return _compliance_unverified("D8.4", "Vendor-risk readiness")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_SCORERS: dict[str, Callable[[dict, Path], CriterionScore]] = {
    "D1.1": score_d1_1, "D1.2": score_d1_2, "D1.3": score_d1_3,
    "D2.1": score_d2_1, "D2.2": score_d2_2, "D2.3": score_d2_3, "D2.4": score_d2_4,
    "D3.1": score_d3_1, "D3.2": score_d3_2, "D3.3": score_d3_3, "D3.4": score_d3_4,
    "D4.1": score_d4_1, "D4.2": score_d4_2, "D4.3": score_d4_3, "D4.4": score_d4_4,
    "D5.1": score_d5_1, "D5.2": score_d5_2, "D5.3": score_d5_3, "D5.4": score_d5_4,
    "D6.1": score_d6_1, "D6.2": score_d6_2, "D6.3": score_d6_3, "D6.4": score_d6_4,
    "D7.1": score_d7_1, "D7.2": score_d7_2, "D7.3": score_d7_3, "D7.4": score_d7_4,
    "D8.1": score_d8_1, "D8.2": score_d8_2, "D8.3": score_d8_3, "D8.4": score_d8_4,
}


def score_all(
    scored: dict,
    repo_path: Path,
    *,
    d8_not_applicable: bool = False,
) -> list[CriterionScore]:
    """Run every per-criterion scorer; return a flat list of CriterionScore.

    ``d8_not_applicable`` overrides D8 to N/A across all four sub-criteria.
    Use this when the asset is internal / non-customer-facing / genuinely
    out of compliance scope.
    """
    out: list[CriterionScore] = []
    for criterion_id, scorer in _SCORERS.items():
        if d8_not_applicable and criterion_id.startswith("D8."):
            out.append(
                CriterionScore(
                    criterion_id=criterion_id,
                    value=NOT_APPLICABLE,
                    evidence=["--d8-not-applicable: out of scope for this assessment"],
                    rationale=(
                        "D8 marked not-applicable by caller (e.g., internal "
                        "tool with no compliance scope)."
                    ),
                )
            )
            continue
        out.append(scorer(scored, repo_path))
    return out


__all__ = ["score_all"]
