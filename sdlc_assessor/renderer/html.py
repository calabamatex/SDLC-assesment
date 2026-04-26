"""HTML renderer for ``sdlc render --format html`` (SDLC-064).

Mirrors the 11-section structure of ``renderer.markdown.render_markdown_report``
but produces a single-file ``report.html`` with an embedded stylesheet and a
sortable findings table (vanilla JS — no external assets, runs offline).

Design notes:

- Keep the CSS minimal and screen-safe; we don't want to ship a design system.
- Use semantic HTML (``<table>``, ``<th>``, ``<section>``) so the report is
  also reasonable when piped through a text-mode browser.
- All strings are escaped through ``html.escape`` to prevent XSS via finding
  statements (the assessor reads code that may contain quotes or angle
  brackets).
"""

from __future__ import annotations

import html
import warnings
from collections import defaultdict
from datetime import UTC, datetime

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
_CONFIDENCE_RANK = {"high": 1.0, "medium": 0.9, "low": 0.7}

_INVENTORY_FIELDS = (
    ("source_files", "Source files"),
    ("source_loc", "Source LOC"),
    ("test_files", "Test files"),
    ("estimated_test_cases", "Estimated test cases"),
    ("test_to_source_ratio", "Test-to-source ratio"),
    ("workflow_files", "Workflow files"),
    ("workflow_jobs", "Workflow jobs"),
    ("runtime_dependencies", "Runtime dependencies"),
    ("dev_dependencies", "Dev dependencies"),
    ("commit_count", "Commit count"),
    ("tag_count", "Tag count"),
    ("release_count", "Release count"),
)

_STYLESHEET = """
:root {
  --bg: #ffffff;
  --fg: #1d1d1f;
  --muted: #6b6b6f;
  --accent: #0058a3;
  --border: #d8d8dc;
  --row-alt: #f7f7f8;
  --critical-bg: #fbeaea;
  --high-bg: #fff0e0;
  --medium-bg: #fff8d6;
  --low-bg: #eef5ff;
  --info-bg: #f0f0f0;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--fg);
  background: var(--bg);
  max-width: 1080px;
  margin: 2.5rem auto;
  padding: 0 1.5rem;
  line-height: 1.5;
}
h1 { font-size: 1.9rem; margin-bottom: 0.25rem; }
h2 { margin-top: 2.2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }
h3 { margin-top: 1.6rem; }
code { font-family: SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.92em; background: var(--row-alt); padding: 0.1em 0.3em; border-radius: 3px; }
table { border-collapse: collapse; width: 100%; font-size: 0.94em; margin: 0.6rem 0 1.4rem; }
th, td { padding: 0.4rem 0.6rem; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--row-alt); cursor: pointer; user-select: none; }
th[aria-sort="ascending"]::after { content: " ▲"; color: var(--accent); }
th[aria-sort="descending"]::after { content: " ▼"; color: var(--accent); }
tr:nth-child(even) td { background: var(--row-alt); }
.sev-critical td:first-child { background: var(--critical-bg); font-weight: 600; }
.sev-high td:first-child { background: var(--high-bg); font-weight: 600; }
.sev-medium td:first-child { background: var(--medium-bg); }
.sev-low td:first-child { background: var(--low-bg); }
.sev-info td:first-child { background: var(--info-bg); color: var(--muted); }
.kv { display: grid; grid-template-columns: 240px 1fr; gap: 0.3rem 1.2rem; margin: 0.4rem 0 1.2rem; }
.kv dt { color: var(--muted); }
.verdict-pass { color: #1a7d3a; font-weight: 600; }
.verdict-pass_with_distinction { color: #1a7d3a; font-weight: 700; }
.verdict-conditional_pass { color: #b56700; font-weight: 600; }
.verdict-fail { color: #b00020; font-weight: 700; }
.muted { color: var(--muted); font-size: 0.92em; }
.banner { padding: 0.8rem 1rem; border-left: 4px solid var(--accent); background: var(--row-alt); margin: 1rem 0 1.5rem; }
"""

_SORT_SCRIPT = """
document.querySelectorAll('table.sortable').forEach(function(t) {
  t.querySelectorAll('th').forEach(function(th, idx) {
    th.addEventListener('click', function() {
      var rows = Array.from(t.querySelectorAll('tbody tr'));
      var current = th.getAttribute('aria-sort');
      var next = current === 'ascending' ? 'descending' : 'ascending';
      t.querySelectorAll('th').forEach(function(o) { o.removeAttribute('aria-sort'); });
      th.setAttribute('aria-sort', next);
      rows.sort(function(a, b) {
        var av = a.children[idx].getAttribute('data-sort') || a.children[idx].textContent.trim();
        var bv = b.children[idx].getAttribute('data-sort') || b.children[idx].textContent.trim();
        var an = parseFloat(av); var bn = parseFloat(bv);
        if (!Number.isNaN(an) && !Number.isNaN(bn)) {
          return next === 'ascending' ? an - bn : bn - an;
        }
        return next === 'ascending' ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      var tbody = t.querySelector('tbody');
      rows.forEach(function(r) { tbody.appendChild(r); });
    });
  });
});
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True) if value is not None else ""


def _normalize_category_scores(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        warnings.warn(
            "scoring.category_scores is in the legacy dict shape; converting "
            "for HTML rendering. Update upstream to the list-of-dicts shape.",
            DeprecationWarning,
            stacklevel=2,
        )
        out = []
        for cat, data in raw.items():
            applicability = data.get("applicability", "applicable")
            out.append(
                {
                    "category": cat,
                    "applicable": applicability != "not_applicable",
                    "score": int(round(data.get("score", 0))),
                    "max_score": int(round(data.get("max", data.get("max_score", 0)))),
                    "summary": data.get("summary", ""),
                    "key_findings": data.get("key_findings", []),
                }
            )
        return out
    return []


def _finding_rank(f: dict) -> float:
    sev = _SEVERITY_RANK.get(f.get("severity", "low"), 0)
    conf = _CONFIDENCE_RANK.get(f.get("confidence", "medium"), 0.0)
    mag = float(f.get("score_impact", {}).get("magnitude", 0)) / 10.0
    return sev * conf * mag


def _executive_summary_html(scored: dict, top_findings: list[dict]) -> list[str]:
    scoring = scored.get("scoring", {}) or {}
    classification = scored.get("classification", {}) or {}
    archetype = _esc(classification.get("repo_archetype", "unknown"))
    confidence = float(classification.get("classification_confidence") or 0.0)
    overall = scoring.get("overall_score", "n/a")
    verdict = scoring.get("verdict", "n/a")
    verdict_class = f"verdict-{_esc(verdict)}"

    paragraphs = [
        f'<p>Overall the repository scored <strong>{_esc(overall)}/100</strong> with a verdict of '
        f'<span class="{verdict_class}">{_esc(verdict)}</span>, on a classification of '
        f'<strong>{archetype}</strong> '
        f'(classification confidence {confidence:.2f}).</p>'
    ]
    if top_findings:
        bullets = "; ".join(
            f'<code>{_esc(f.get("subcategory", "?"))}</code> ({_esc(f.get("severity", "?"))})'
            for f in top_findings[:3]
        )
        paragraphs.append(f"<p>Top issues by severity × confidence × magnitude: {bullets}.</p>")
    else:
        paragraphs.append("<p>No findings were emitted by the detector packs for this repository.</p>")

    blockers = scored.get("hard_blockers") or []
    if blockers:
        critical = sum(1 for b in blockers if b.get("severity") == "critical")
        high = sum(1 for b in blockers if b.get("severity") == "high")
        paragraphs.append(
            f"<p>Hard blockers active: {critical} critical, {high} high. See §8 below.</p>"
        )
    else:
        paragraphs.append("<p>No hard blockers were triggered for this profile.</p>")
    return paragraphs


def _findings_table_html(findings: list[dict]) -> str:
    if not findings:
        return '<p class="muted">No findings to display.</p>'
    rows: list[str] = []
    for f in findings:
        sev = (f.get("severity") or "info").lower()
        ev = (f.get("evidence") or [{}])[0]
        path = _esc(ev.get("path", "n/a"))
        line = ev.get("line_start")
        path_ref = f"{path}:{line}" if line else path
        sub = _esc(f.get("subcategory", "?"))
        cat = _esc(f.get("category", "?"))
        stmt = _esc(f.get("statement", ""))
        sev_rank = _SEVERITY_RANK.get(sev, 0)
        rows.append(
            f'<tr class="sev-{_esc(sev)}">'
            f'<td data-sort="{sev_rank}">{_esc(sev.upper())}</td>'
            f'<td>{cat}</td>'
            f'<td><code>{sub}</code></td>'
            f'<td>{stmt}</td>'
            f'<td><code>{_esc(path_ref)}</code></td>'
            f'</tr>'
        )
    rows_html = "\n        ".join(rows)
    return (
        '<table class="sortable">\n'
        '  <thead>\n'
        '    <tr><th>Severity</th><th>Category</th><th>Subcategory</th><th>Statement</th><th>Location</th></tr>\n'
        '  </thead>\n'
        f'  <tbody>\n        {rows_html}\n  </tbody>\n'
        '</table>'
    )


def _category_scoring_table_html(category_scores: list[dict]) -> str:
    rows: list[str] = []
    for cat in category_scores:
        applicable = "yes" if cat.get("applicable") else "no"
        if not cat.get("applicable"):
            score_cell, max_cell = "—", "—"
        else:
            score_cell = _esc(cat.get("score", 0))
            max_cell = _esc(cat.get("max_score", 0))
        summary = _esc(cat.get("summary", ""))
        rows.append(
            f"<tr>"
            f"<td>{_esc(cat.get('category', '?'))}</td>"
            f"<td>{applicable}</td>"
            f"<td>{score_cell}</td>"
            f"<td>{max_cell}</td>"
            f"<td>{summary}</td>"
            f"</tr>"
        )
    rows_html = "\n        ".join(rows)
    return (
        '<table class="sortable">\n'
        '  <thead><tr><th>Category</th><th>Applicable</th><th>Score</th><th>Max</th><th>Summary</th></tr></thead>\n'
        f'  <tbody>\n        {rows_html}\n  </tbody>\n'
        '</table>'
    )


def _findings_grouped_html(findings: list[dict]) -> str:
    if not findings:
        return '<p class="muted">No findings to display.</p>'
    bucket: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        bucket[f.get("category", "unknown")].append(f)
    blocks: list[str] = []
    for cat in sorted(bucket.keys()):
        sorted_findings = sorted(
            bucket[cat],
            key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "low"), 5),
        )
        items: list[str] = []
        for f in sorted_findings:
            sev = (f.get("severity") or "info").lower()
            stmt = _esc(f.get("statement", ""))
            ev = (f.get("evidence") or [{}])[0]
            path = ev.get("path", "")
            line = ev.get("line_start")
            path_ref = f"{path}:{line}" if line else path
            items.append(
                f'<li class="sev-{_esc(sev)}">'
                f'<strong>{_esc(sev.upper())}</strong> {stmt} — '
                f'<code>{_esc(path_ref)}</code>'
                f'</li>'
            )
        items_html = "\n        ".join(items)
        blocks.append(
            f"<h3>{_esc(cat)}</h3>\n"
            f'<ul>\n        {items_html}\n      </ul>'
        )
    return "\n".join(blocks)


def render_html_report(scored: dict) -> str:
    repo_meta = scored.get("repo_meta", {}) or {}
    classification = scored.get("classification", {}) or {}
    scoring = scored.get("scoring", {}) or {}
    blockers = scored.get("hard_blockers") or []
    inventory = scored.get("inventory", {}) or {}
    findings = scored.get("findings") or []
    category_scores = _normalize_category_scores(scoring.get("category_scores", []))
    ranked = sorted(findings, key=lambda f: -_finding_rank(f))

    eff = scoring.get("effective_profile", {}) or {}
    page_title = f"SDLC Assessment — {_esc(repo_meta.get('name', 'unknown'))}"

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append(f"<title>{page_title}</title>")
    parts.append(f'<style>{_STYLESHEET}</style>')
    parts.append("</head>")
    parts.append("<body>")

    # §1 Header
    parts.append(f"<h1>{page_title}</h1>")
    parts.append(
        '<p class="muted">'
        f"Branch <code>{_esc(repo_meta.get('default_branch', 'unknown'))}</code> · "
        f"Analysis {_esc(repo_meta.get('analysis_timestamp', datetime.now(UTC).isoformat()))} · "
        f"Use-case <code>{_esc(eff.get('use_case', 'n/a'))}</code> · "
        f"Maturity <code>{_esc(eff.get('maturity', 'n/a'))}</code> · "
        f"Repo type <code>{_esc(eff.get('repo_type', 'n/a'))}</code>"
        "</p>"
    )

    # §2 Executive summary
    parts.append("<h2>2. Executive Summary</h2>")
    parts.extend(_executive_summary_html(scored, ranked))

    # §3 Overall + verdict (banner)
    overall = scoring.get("overall_score", "n/a")
    verdict = scoring.get("verdict", "n/a")
    parts.append('<div class="banner">')
    parts.append(
        f"<strong>Overall:</strong> {_esc(overall)}/100 · "
        f"<strong>Verdict:</strong> "
        f'<span class="verdict-{_esc(verdict)}">{_esc(verdict)}</span> · '
        f"<strong>Score confidence:</strong> {_esc(scoring.get('score_confidence', 'n/a'))}"
    )
    parts.append("</div>")

    # §4 Classification box
    parts.append("<h2>4. Repo Classification</h2>")
    parts.append('<dl class="kv">')
    for cls_key, cls_label in (
        ("repo_archetype", "Archetype"),
        ("maturity_profile", "Maturity"),
        ("deployment_surface", "Deployment surface"),
        ("network_exposure", "Network exposure"),
        ("release_surface", "Release surface"),
        ("classification_confidence", "Classification confidence"),
    ):
        parts.append(f"<dt>{cls_label}</dt><dd>{_esc(classification.get(cls_key, 'unknown'))}</dd>")
    parts.append("</dl>")

    # §5 Inventory
    parts.append("<h2>5. Quantitative Inventory</h2>")
    parts.append('<dl class="kv">')
    for key, label in _INVENTORY_FIELDS:
        value = inventory.get(key)
        parts.append(f"<dt>{label}</dt><dd>{_esc(value if value is not None else 'n/a')}</dd>")
    parts.append("</dl>")

    # §6 Top strengths
    parts.append("<h2>6. Top Strengths</h2>")
    strong = [
        c for c in category_scores
        if c.get("applicable") and c.get("max_score", 0) > 0
        and c.get("score", 0) >= c.get("max_score", 0)
    ]
    if not strong:
        parts.append(
            '<p class="muted">No category earned full points; see §7 Top Risks and '
            "§10 Detailed Findings for the gaps.</p>"
        )
    else:
        bullets = "".join(
            f'<li><strong>{_esc(c["category"])}</strong> retained full points '
            f'({_esc(c["score"])}/{_esc(c["max_score"])}).</li>'
            for c in strong[:5]
        )
        parts.append(f"<ul>{bullets}</ul>")

    # §7 Top risks
    parts.append("<h2>7. Top Risks</h2>")
    if not findings:
        parts.append('<p class="muted">No explicit risks detected.</p>')
    else:
        items = []
        for f in ranked[:5]:
            sev = (f.get("severity") or "info").upper()
            stmt = _esc(f.get("statement", ""))
            ev = (f.get("evidence") or [{}])[0]
            path = ev.get("path", "n/a")
            line = ev.get("line_start")
            path_ref = f"{path}:{line}" if line else path
            conf = _esc(f.get("confidence", "?"))
            sev_class = f.get("severity", "info").lower()
            items.append(
                f'<li class="sev-{sev_class}">'
                f"<strong>{_esc(sev)}</strong> {stmt} — "
                f"<code>{_esc(path_ref)}</code> "
                f'<span class="muted">(confidence {conf})</span>'
                f"</li>"
            )
        parts.append(f"<ul>{''.join(items)}</ul>")

    # §8 Hard blockers
    parts.append("<h2>8. Hard Blockers</h2>")
    if not blockers:
        parts.append('<p class="muted">No hard blockers were triggered.</p>')
    else:
        items = []
        for b in blockers:
            sev = (b.get("severity") or "?").upper()
            title = _esc(b.get("title", "(no title)"))
            reason = _esc(b.get("reason", ""))
            closure = b.get("closure_requirements") or []
            closure_html = (
                "<ul>" + "".join(f"<li>{_esc(c)}</li>" for c in closure) + "</ul>"
                if closure else ""
            )
            items.append(
                f'<li class="sev-{(b.get("severity") or "info").lower()}">'
                f"<strong>{_esc(sev)}</strong> {title} — {reason}{closure_html}"
                f"</li>"
            )
        parts.append(f"<ul>{''.join(items)}</ul>")

    # §9 Category scoring matrix
    parts.append("<h2>9. Category Scoring Matrix</h2>")
    parts.append(_category_scoring_table_html(category_scores))

    # §10 Detailed findings (sortable table) + grouped breakdown
    parts.append("<h2>10. Detailed Findings</h2>")
    parts.append("<h3>10.1 Sortable findings table</h3>")
    parts.append(_findings_table_html(findings))
    parts.append("<h3>10.2 Findings by category</h3>")
    parts.append(_findings_grouped_html(findings))

    # §11 Evidence appendix
    parts.append("<h2>11. Evidence Appendix</h2>")
    parts.append(f"<p>Total findings: {len(findings)}</p>")

    parts.append(f"<script>{_SORT_SCRIPT}</script>")
    parts.append("</body></html>")

    return "\n".join(parts) + "\n"


__all__ = ["render_html_report"]
