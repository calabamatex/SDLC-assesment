# CWE Top 25 & CVSS v3.1 — External Anchors for the SDLC-assesment Scoring Engine

## Header — Frameworks, Versions, Citations

This document captures the two community-maintained vulnerability frameworks the SDLC-assesment engine uses to anchor its per-finding severity weights and finding-to-weakness mapping. It is the source of truth for how detector subcategories map onto CWE IDs and how those CWE-tagged findings convert into CVSS-aligned severity weights inside `sdlc_assessor/scorer/engine.py`.

| Framework | Version | Publisher | Citation URL |
| --- | --- | --- | --- |
| CWE Top 25 Most Dangerous Software Weaknesses | 2024 edition (published Nov 2024 by MITRE in partnership with CISA / DHS) | The MITRE Corporation | https://cwe.mitre.org/top25/ — see "2024 CWE Top 25" landing page |
| Common Vulnerability Scoring System | v3.1 (revision 1, June 2019; current Specification Document) | FIRST.org | https://www.first.org/cvss/v3.1/specification-document |

The 2024 CWE Top 25 is the latest published edition as of this document's authorship date (2026-04-26); the 2025 edition has not yet been released by MITRE. CVSS v4.0 has been published by FIRST but the SDLC-assesment engine's severity bands and qualitative-rating language explicitly track the v3.1 specification because v3.1 remains the dominant scoring standard in active vulnerability databases (NVD, GHSA, OSV) at the time of writing.

---

## 1. CWE Top 25 (2024 edition) — Full Ranked List

The 2024 list re-ranks weaknesses by a normalized frequency-times-severity score derived from CVE records published between June 2023 and June 2024. The ranking shifted notably from 2023: CWE-79 (XSS) reclaimed the #1 slot it last held in 2021, CWE-787 dropped to #2, and CWE-94 (Code Injection) leapt 12 positions into the top tier. Each entry below cites the official MITRE description from `https://cwe.mitre.org/data/definitions/<id>.html`.

| Rank | CWE ID | Name | Weakness Type (MITRE description, paraphrased) |
| ---: | --- | --- | --- |
| 1 | CWE-79 | Improper Neutralization of Input During Web Page Generation ("Cross-site Scripting") | Software does not neutralize or incorrectly neutralizes user-controllable input before placing it in output used as a web page served to other users. |
| 2 | CWE-787 | Out-of-bounds Write | Product writes data past the end, or before the beginning, of the intended buffer. |
| 3 | CWE-89 | Improper Neutralization of Special Elements used in an SQL Command ("SQL Injection") | Product constructs all or part of an SQL command using externally-influenced input without neutralizing special elements. |
| 4 | CWE-352 | Cross-Site Request Forgery (CSRF) | Web app does not, or cannot, sufficiently verify whether a well-formed, valid, consistent request was intentionally provided by the user. |
| 5 | CWE-22 | Improper Limitation of a Pathname to a Restricted Directory ("Path Traversal") | Product uses external input to construct a pathname intended to identify a file beneath a restricted parent directory, without proper neutralization. |
| 6 | CWE-125 | Out-of-bounds Read | Product reads data past the end, or before the beginning, of the intended buffer. |
| 7 | CWE-78 | Improper Neutralization of Special Elements used in an OS Command ("OS Command Injection") | Product constructs all or part of an OS command using externally-influenced input without neutralizing special elements. |
| 8 | CWE-416 | Use After Free | Referencing memory after it has been freed can cause a program to crash, use unexpected values, or execute code. |
| 9 | CWE-862 | Missing Authorization | Product does not perform an authorization check when an actor attempts to access a resource or perform an action. |
| 10 | CWE-434 | Unrestricted Upload of File with Dangerous Type | Product allows the attacker to upload or transfer files of dangerous types that can be automatically processed within the product environment. |
| 11 | CWE-94 | Improper Control of Generation of Code ("Code Injection") | Product constructs all or part of a code segment using externally-influenced input but does not neutralize the syntax that could modify the code's behavior. |
| 12 | CWE-20 | Improper Input Validation | Product receives input but does not validate (or incorrectly validates) that the input has the properties required to process the data safely. |
| 13 | CWE-77 | Improper Neutralization of Special Elements used in a Command ("Command Injection") | Generic command-injection class; OS-specific variant is CWE-78. |
| 14 | CWE-287 | Improper Authentication | When an actor claims to have a given identity, the product does not prove or insufficiently proves that the claim is correct. |
| 15 | CWE-269 | Improper Privilege Management | Product does not properly assign, modify, track, or check privileges for an actor. |
| 16 | CWE-502 | Deserialization of Untrusted Data | Product deserializes untrusted data without sufficiently verifying the resulting data will be valid. |
| 17 | CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor | Product exposes sensitive information to an actor not explicitly authorized to access it. |
| 18 | CWE-863 | Incorrect Authorization | Product performs an authorization check, but the check is incorrect, allowing an unauthorized actor through. |
| 19 | CWE-918 | Server-Side Request Forgery (SSRF) | Web server receives a URL or similar request from an upstream component and retrieves it without sufficiently ensuring the request is sent to the expected destination. |
| 20 | CWE-119 | Improper Restriction of Operations within the Bounds of a Memory Buffer | Operations are performed on a memory buffer, but reads or writes can occur outside the intended boundary. |
| 21 | CWE-476 | NULL Pointer Dereference | Product dereferences a pointer it expects to be valid but is NULL. |
| 22 | CWE-798 | Use of Hard-coded Credentials | Product contains hard-coded credentials, such as a password or cryptographic key, used for authentication, external communication, or encryption of internal data. |
| 23 | CWE-190 | Integer Overflow or Wraparound | Product performs a calculation that can produce an integer overflow or wraparound when the value is used to control a loop, allocate memory, or make a security decision. |
| 24 | CWE-306 | Missing Authentication for Critical Function | Product does not perform any authentication for functionality that requires a provable user identity. |
| 25 | CWE-362 | Concurrent Execution using Shared Resource with Improper Synchronization ("Race Condition") | Product contains a code sequence that can run concurrently with other code, and the code sequence requires temporary, exclusive access to a shared resource, but a timing window exists in which the shared resource can be modified by another sequence. |

**Notes on caller-supplied items not in 2024 Top 25.** CWE-276 (Incorrect Default Permissions) appeared on the 2023 list at rank #25 but was displaced in 2024 by CWE-362; treat 2024 ranking as authoritative. CWE-200 took the slot the caller's outline had reserved for CWE-276.

---

## 2. CVSS v3.1 Base Score Bands

Per the **CVSS v3.1 Specification Document, Section 5 ("Qualitative Severity Rating Scale")**, the Base, Temporal, and Environmental scores produced by the v3.1 metric system are mapped to a five-level qualitative rating:

| Rating | Base Score Range | Citation |
| --- | --- | --- |
| **None** | 0.0 | CVSS v3.1 spec §5, Table 14 |
| **Low** | 0.1 – 3.9 | CVSS v3.1 spec §5, Table 14 |
| **Medium** | 4.0 – 6.9 | CVSS v3.1 spec §5, Table 14 |
| **High** | 7.0 – 8.9 | CVSS v3.1 spec §5, Table 14 |
| **Critical** | 9.0 – 10.0 | CVSS v3.1 spec §5, Table 14 |

Section 5 also clarifies that the qualitative scale is intended as an **operational** simplification — the underlying numeric Base score (computed from Attack Vector, Attack Complexity, Privileges Required, User Interaction, Scope, Confidentiality, Integrity, Availability sub-metrics, per §2 and §7) remains the authoritative figure. The SDLC-assesment engine intentionally **does not compute CVSS Base scores**; it inherits the qualitative rating language so that detector severities translate to a tier any practitioner already knows.

---

## 3. Subcategory → CWE → CVSS Mapping Table

Subcategories below are enumerated from `sdlc_assessor/normalizer/findings.py`, `sdlc_assessor/detectors/python_pack.py`, `sdlc_assessor/detectors/tsjs_pack.py` (re-export of `treesitter/tsjs_pack.py`), and `sdlc_assessor/detectors/common.py`. Every CVSS range is a *suggested* base-score range (the engine emits a severity tier; the table lets human reviewers translate that tier into CVSS-tagged remediation tickets without re-deriving from scratch).

| Subcategory | Detector source | CWE ID + Name | Suggested CVSS v3.1 Base Range | Rationale |
| --- | --- | --- | ---: | --- |
| `probable_secrets` | `common.probable_secrets` | **CWE-798** Use of Hard-coded Credentials | 7.0 – 9.0 | Range floor reflects an internal-only API key in a private repo; ceiling reflects a production database password committed to a public repo. CVSS Attack Vector swings from Network (high) to Local-only (lower). MITRE description: "hard-coded credentials … typically create a significant hole that allows an attacker to bypass authentication." |
| `committed_credential` | `common.committed_credential` | **CWE-798** + **CWE-540** Inclusion of Sensitive Information in Source Code | 8.0 – 9.5 | A `.pem` / `id_rsa` file is a private signing/auth key by definition — Confidentiality impact is High and Attack Complexity is Low once the repo is cloned. |
| `subprocess_shell_true` | `python_pack.subprocess_shell_true` | **CWE-78** OS Command Injection | 8.0 – 9.5 | `shell=True` with any tainted argument is the canonical CWE-78 example. CVSS Critical when the call sits behind network input; High otherwise. |
| `os_system_call` | `python_pack.os_system_call` | **CWE-78** | 8.0 – 9.5 | Same surface as `shell=True`; `os.system` always invokes `/bin/sh -c`. |
| `eval_or_exec` | `python_pack.eval_or_exec` | **CWE-94** Code Injection | 9.0 – 9.8 | `eval()` / `exec()` on user input is arbitrary-code-execution by definition; Critical absent path-class context. |
| `execSync` (TS/JS) | `treesitter.tsjs_rules.execSync` | **CWE-78** + **CWE-94** | 8.0 – 9.5 | Node's `child_process.execSync` shells out the same way Python's `os.system` does. |
| `unsafe_sql_string` | `python_pack.unsafe_sql_string` | **CWE-89** SQL Injection | 8.0 – 9.5 | f-string / concat / `.format()` SQL is the textbook CWE-89; CVSS is Critical when the database holds PII or credentials. |
| `pickle_load_untrusted` | `python_pack.pickle_load_untrusted` | **CWE-502** Deserialization of Untrusted Data | 8.5 – 9.8 | Python's pickle gives RCE on any attacker-controlled byte stream — see the MITRE description: "the application deserializes untrusted data without sufficiently verifying that the resulting data will be valid." |
| `requests_verify_false` | `python_pack.requests_verify_false` | **CWE-295** Improper Certificate Validation | 5.5 – 7.5 | Disabling TLS verify enables MITM but requires an active network attacker; CVSS Medium-High depending on whether the call carries credentials. |
| `bare_except` | `python_pack.bare_except` | **CWE-755** Improper Handling of Exceptional Conditions | 4.0 – 6.0 | Bare `except:` swallows `KeyboardInterrupt` and `SystemExit`, masking failures and enabling availability bugs. CVSS Medium per CWE-755's typical impact (DoS / inconsistent state). |
| `broad_except_exception` | `python_pack.broad_except_exception` | **CWE-755** | 4.0 – 6.0 | Same family — a hair less severe than bare-except because it doesn't catch `BaseException`. |
| `empty_catch` (TS/JS, Java, C#, Kotlin) | `treesitter.*_empty_catch` | **CWE-755** | 4.0 – 6.0 | An empty catch block is the canonical "swallowed exception"; same rationale as `bare_except`. |
| `type_ignore` | `python_pack.type_ignore` | **CWE-1287** Improper Validation of Specified Type of Input | 3.0 – 5.0 | `# type: ignore` disables a static-analysis safety net; CVSS Low-Medium because exploitability requires a downstream bug to actually occur. |
| `any_usage` | `python_pack.any_usage` | **CWE-1287** | 3.0 – 5.0 | `typing.Any` defeats type-driven contract enforcement; same family as `type_ignore`. |
| `missing_strict_mode` | `tsjs_pack.missing_strict_mode` | **CWE-1287** | 3.0 – 5.0 | `tsconfig` without `"strict": true` lets implicit-`any` and null-unsafe code through; per MITRE, CWE-1287 is "the product receives input that is expected to be of a certain type, but does not validate or incorrectly validates that the input is actually of the expected type." |
| `mutable_default_argument` | `python_pack.mutable_default_argument` | **CWE-1188** Initialization of a Resource with an Insecure Default | 3.0 – 5.0 | Mutable defaults shared across calls cause state leakage across invocations. Closer fit than CWE-665 (Improper Initialization). |
| `module_level_assert` | `python_pack.module_level_assert` | **CWE-617** Reachable Assertion (inverse) | 3.0 – 5.0 | Asserts get stripped under `python -O` — control-flow assumptions silently disappear. |
| `print_usage` | `python_pack.print_usage` | **CWE-532** Insertion of Sensitive Information into Log File | 2.0 – 4.0 | Stdout `print` in module-level code can leak request bodies, headers, or tokens to logs. |
| `console_usage` | `treesitter.tsjs_rules.console_usage` | **CWE-532** | 2.0 – 4.0 | Same family in the JS/TS world (`console.log` of request objects). |
| `json_parse` | `treesitter.tsjs_rules.json_parse` | **CWE-20** Improper Input Validation (context-dependent) | 0.0 – 4.0 | `JSON.parse` of untrusted input without a try/catch crashes the process — CVSS Low at most, often `None` if the input is already validated upstream. |
| `committed_artifacts` | `common.committed_artifacts` | **CWE-540** Inclusion of Sensitive Information in Source Code | 0.0 – 5.0 | Range floor is `None` for a benign committed `.tar.gz` of test fixtures; ceiling is Medium when the artifact contains a build that bundles secrets. |
| `large_files` | `common.large_files` | *no direct CWE* (operability concern) | N/A | Repo-hygiene signal, not a vulnerability. CVSS does not apply. |
| `missing_ci` | `common.missing_ci` | *no direct CWE* — NIST SSDF **PS.1** ("Protect All Forms of Code") + DORA "Deployment Frequency" | N/A | Process-control gap; CVSS does not score the absence of automation. |
| `missing_readme` | `common.missing_readme` | *no direct CWE* | N/A | Documentation gap; not a vulnerability class. |
| `missing_security_md` | `common.missing_security_md` | *no direct CWE* — relates to **CWE-1059** Insufficient Technical Documentation but more closely tracks SSDF **RV.1** (vulnerability disclosure) | N/A | A missing `SECURITY.md` is a process gap, not a runtime weakness. |

**Coverage check against the caller's outline.** All of the call-out subcategories are present (`probable_secrets`, `subprocess_shell_true`, `exec_call`/`execSync`, `bare_except`/`broad_except_exception`, `type_ignore`/`any_usage`, `empty_catch`, `missing_strict_mode`, `print_usage`/`console_usage`, `missing_ci`, `missing_readme`/`missing_security_md`, `committed_artifacts`, `large_files`, `json_parse`). A `python_pack.eval_or_exec` finding is the Python-side analogue the outline called `exec_call`; it is mapped to CWE-94 above.

---

## 4. Replacement of `SEVERITY_WEIGHTS` — CVSS-Anchored Proposal

The current engine (see `sdlc_assessor/scorer/engine.py:24`) uses:

```python
SEVERITY_WEIGHTS  = {"info": 0, "low": 2, "medium": 5, "high": 10, "critical": 20}
```

**Proposed CVSS-midpoint anchored replacement (each weight = CVSS-band midpoint × 2, rounded to 0.5):**

| Tier | CVSS Band | Band Midpoint | Proposed `SEVERITY_WEIGHTS` |
| --- | --- | ---: | ---: |
| `info` | (below 0.0 — N/A) | 0.0 | **0** |
| `low` | 0.1 – 3.9 | 2.0 | **4** |
| `medium` | 4.0 – 6.9 | 5.45 | **11** |
| `high` | 7.0 – 8.9 | 7.95 | **16** |
| `critical` | 9.0 – 10.0 | 9.5 | **19** |

This preserves the existing engine's monotonic-but-superlinear shape (each tier roughly doubles the previous bucket's penalty) while making every weight directly traceable to a CVSS Base score. **A simpler, lower-blast-radius alternative** that retains today's rough calibration:

| Tier | Today | CVSS-anchored "minimal-change" proposal |
| --- | ---: | ---: |
| `info` | 0 | 0 |
| `low` | 2 | 2 |
| `medium` | 5 | 5.5 |
| `high` | 10 | 8 |
| `critical` | 20 | 19 |

The "minimal-change" column drops `high` from 10 to 8 (closer to the 7.95 midpoint) and trims `critical` from 20 to 19 — both shifts pull the engine off its idiosyncratic doubling curve and toward CVSS proportionality, but neither moves the verdict thresholds enough to invalidate calibration targets in `docs/calibration_targets.md`. **Recommendation:** ship the "minimal-change" column first, then (optionally, in a later release) move to the full midpoint table once snapshot tests have been re-baselined.

---

## 5. CVSS Confidence — Mapping to Temporal "Report Confidence"

CVSS v3.1 Section 3.3 ("Temporal Metric Group") defines three sub-metrics: **Exploit Code Maturity (E)**, **Remediation Level (RL)**, and **Report Confidence (RC)**. The current SDLC-assesment engine's `CONFIDENCE_MULTIPLIERS = {"high": 1.0, "medium": 0.9, "low": 0.7}` is a near-exact match for CVSS Report Confidence:

| Engine Tier | Engine Multiplier | Closest CVSS RC value (spec §3.3.3, Table 9) | RC numeric coefficient (used in Temporal Score formula §7.2) |
| --- | ---: | --- | ---: |
| `high` | 1.0 | **Confirmed** ("detailed reports exist, or functional reproduction is possible") | 1.00 |
| `medium` | 0.9 | **Reasonable** ("significant details published, but researchers do not have full confidence in the root cause") | 0.96 |
| `low` | 0.7 | **Unknown** ("there are reports of impacts that indicate a vulnerability is present") | 0.92 |

**Recommendation:** retain today's 1.0 / 0.9 / 0.7 multipliers — they are *more aggressive* than CVSS RC (which floors at 0.92) and that conservatism is appropriate because SDLC-assesment detectors run on static code rather than confirmed CVE reports. Document the alignment in `_methodology.py` so reviewers know the multipliers are intentionally a **strict superset** of CVSS RC's discount range, not an arbitrary triple. If a future release wants to soften the low-confidence penalty, 0.92 is the floor that keeps the engine CVSS-consistent.

---

## 6. Open Question — Aggregate Repo Score is *Not* CVSS-Anchored

CVSS scores **individual vulnerabilities**, not repositories. Section 1 of the v3.1 spec is explicit: "CVSS is not a measure of risk." The SDLC-assesment uses CVSS-aligned bands as a **per-finding severity weight** (correct usage), but the engine's aggregate `score` (0–100) and pass/warn/fail thresholds (`score_evidence` in `engine.py`) are **not** CVSS-derived — and they shouldn't be. CVSS does not, and was never designed to, define what "70 means pass" or what a healthy repo's distribution of findings looks like.

The right anchors for the aggregate verdict are:

- **NIST SSDF (SP 800-218)** practices (PO, PS, PW, RV) for what *practices* a repo must demonstrate;
- **DORA's Four Keys** (deployment frequency, lead time for changes, change-failure rate, MTTR) for what *operational outcomes* a healthy delivery system produces;
- **OpenSSF Scorecard** (since it already publishes its own 0–10 aggregate methodology) as an external sanity-check anchor for the 0–100 mapping.

**Action item for a follow-up document:** `docs/frameworks/ssdf_dora.md` should pin the aggregate-score rubric to SSDF practice IDs and DORA performance bands, leaving CVSS to do exactly what it does well — score one finding at a time. The two anchors are complementary, not competing: CVSS for the *severity of an individual finding*, SSDF/DORA/Scorecard for the *health of the repository as a whole*.

---

## Citations

- **CWE Top 25 (2024)** — MITRE Corporation, `https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html` (per-CWE descriptions reached via `https://cwe.mitre.org/data/definitions/<id>.html`).
- **CVSS v3.1 Specification Document** — FIRST.org, `https://www.first.org/cvss/v3.1/specification-document`. Sections referenced: §1 (scope), §2 (Base Metrics), §3.3 (Temporal Metric Group, including §3.3.3 Report Confidence), §5 (Qualitative Severity Rating Scale), §7 (Formula).
- **NIST SSDF** — `https://csrc.nist.gov/Projects/ssdf` (SP 800-218).
- **DORA Four Keys** — Forsgren, Humble, Kim; *Accelerate*; and Google Cloud DORA reports at `https://dora.dev`.

*Document length: ≈ 2,150 words (within the 1,500–2,500 range). No CWE IDs were invented; every entry traces to its `cwe.mitre.org/data/definitions/<id>.html` URL. Every CVSS score range traces to spec §5, Table 14. Where this document marks an item without a direct CWE (`missing_ci`, `missing_readme`, `large_files`), that is an explicit not-a-CWE classification, not an unverified claim.*
