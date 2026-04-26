"""Modern HTML renderer for persona deliverables (SDLC-079).

Replaces the v0.9.0 page layout (a single template with sections injected)
with a *document-grade* layout that mirrors the persona-distinct
:class:`Deliverable` shape:

- Cover sheet with the recommendation pill and the score gauge as the
  single dominant visual.
- Body sections rendered per ``Section.kind``:
    * ``prose`` — paragraphs.
    * ``facts`` — definition-style fact strip + optional paragraphs.
    * ``chart`` — full-bleed SVG with caption.
    * ``swot`` — four-quadrant grid.
    * ``day_n`` — three side-by-side cards (Day-30 / 60 / 90).
    * ``options_ladder`` / recommendation block — verdict ladder with
      conditions and projected score.
    * ``questions`` — numbered list.
    * ``claims_evaluation`` — two-column claim/evidence table.
    * ``remediation_table`` — task table (sortable).
- Engineering appendix at the back (the v0.9.0 finding listing,
  collapsed by default).

The stylesheet is print-friendly (A4 page-breaks, page-margin guidance,
no JS required for the main flow). Sortable tables use a single small
script kept inline so the report works offline.
"""

from __future__ import annotations

import html as _html
import warnings
from collections import defaultdict
from datetime import UTC, datetime

from sdlc_assessor.normalizer.findings import is_fixture_finding
from sdlc_assessor.profiles.loader import load_use_case_profiles
from sdlc_assessor.renderer.deliverables import Deliverable, build_deliverable
from sdlc_assessor.renderer.deliverables.base import RecommendationOption

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_VERDICT_LABEL = {
    "proceed": "Proceed",
    "proceed_with_conditions": "Proceed · with conditions",
    "defer": "Defer",
    "decline": "Decline",
}

_NARRATOR_LABEL = {
    "deterministic": "Evidence",
    "llm": "Narrative",
    "both": "Narrative",
}


_STYLESHEET = """
:root {
  --bg: #fbfaf7;
  --surface: #ffffff;
  --ink: #15171c;
  --muted: #5b6370;
  --rule: #e5e3dc;
  --rule-strong: #c9c5b9;
  --accent: #1f3a5f;
  --accent-soft: #eaf0f8;
  --pass-bg: #e3f1e7; --pass-fg: #1a4f2c;
  --distinction-bg: #d9ecf2; --distinction-fg: #134554;
  --conditional-bg: #fdf1d8; --conditional-fg: #715006;
  --fail-bg: #fbe2dc; --fail-fg: #7a1b14;
  --critical-bg: #f7d9d3; --critical-fg: #5c130d;
  --high-bg: #fde2cf; --high-fg: #7d3a06;
  --medium-bg: #fef0c8; --medium-fg: #6c5300;
  --low-bg: #e3edf9; --low-fg: #1d3d70;
  --info-bg: #ebe9e3; --info-fg: #4a4d54;
  --shadow: 0 1px 2px rgba(20, 22, 28, 0.04), 0 4px 16px rgba(20, 22, 28, 0.06);
  --serif: "Charter", "Iowan Old Style", "Source Serif Pro", Georgia, "Times New Roman", serif;
  --sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}

* { box-sizing: border-box; }
html { font-size: 16px; -webkit-font-smoothing: antialiased; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--serif); font-size: 1.02rem; line-height: 1.55;
}

.doc {
  max-width: 880px; margin: 0 auto;
  padding: 3.5rem 4rem 5rem;
}

/* Headline hierarchy */
h1, h2, h3, h4 {
  font-family: var(--sans); color: var(--ink); letter-spacing: -0.01em;
  margin: 0 0 0.5rem;
}
h1 { font-size: 2.4rem; line-height: 1.15; font-weight: 700; }
h2 { font-size: 1.55rem; line-height: 1.25; margin: 3.6rem 0 1.1rem; padding-top: 1.4rem; border-top: 1px solid var(--rule); font-weight: 650; }
h3 { font-size: 1.15rem; line-height: 1.3; margin: 1.6rem 0 0.65rem; font-weight: 600; }
h4 { font-size: 0.92rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin: 1.2rem 0 0.4rem; font-weight: 600; }
p  { margin: 0.5rem 0 1rem; }
.lede { font-size: 1.12rem; line-height: 1.55; color: #2c303a; }

/* Cover */
.cover {
  display: grid; grid-template-columns: 1fr auto;
  gap: 2rem; align-items: center;
  padding: 2.6rem 0 2.4rem;
  border-bottom: 1px solid var(--rule);
}
.cover .meta {
  font-family: var(--sans); font-size: 0.84rem;
  letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted);
}
.cover .title { margin-top: 0.8rem; }
.cover .subtitle { color: var(--muted); font-size: 1.08rem; line-height: 1.4; margin-top: 0.4rem; }
.cover .classification {
  display: inline-block; margin-top: 1rem; padding: 0.25rem 0.7rem;
  background: var(--accent-soft); color: var(--accent);
  font-family: var(--sans); font-size: 0.85rem; border-radius: 999px;
}
.cover .gauge { width: 220px; }
.cover .gauge svg { display: block; max-width: 100%; height: auto; }

/* Recommendation pill */
.recommendation {
  display: flex; flex-direction: column; gap: 0.3rem;
  padding: 1.2rem 1.4rem; margin: 1.2rem 0 1.4rem;
  background: var(--surface); border-radius: 10px;
  box-shadow: var(--shadow);
}
.recommendation .pill {
  display: inline-flex; align-items: center;
  align-self: flex-start;
  padding: 0.32rem 0.85rem;
  border-radius: 999px;
  font-family: var(--sans); font-weight: 600; font-size: 0.9rem; letter-spacing: 0.02em;
}
.pill-proceed                  { background: var(--pass-bg); color: var(--pass-fg); }
.pill-proceed_with_conditions  { background: var(--conditional-bg); color: var(--conditional-fg); }
.pill-defer                    { background: var(--medium-bg); color: var(--medium-fg); }
.pill-decline                  { background: var(--critical-bg); color: var(--critical-fg); }
.recommendation .rationale { color: #2c303a; }

/* Headline-fact strip on the cover */
.headline-facts {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.9rem 1.4rem; margin: 1.4rem 0 0.4rem;
  padding: 1rem 1.2rem; background: var(--surface);
  border-radius: 10px; box-shadow: var(--shadow);
}
.headline-facts .fact .k { font-family: var(--sans); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
.headline-facts .fact .v { font-size: 1.08rem; font-weight: 600; }

/* Sections */
section.kind-prose, section.kind-facts { margin-bottom: 1rem; }

/* Facts (definition-style) */
.facts-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.65rem 1.6rem; margin: 0.6rem 0 1.2rem;
}
.facts-grid .row .k { font-family: var(--sans); font-size: 0.84rem; color: var(--muted); }
.facts-grid .row .v { font-weight: 600; }
.facts-grid .row.sev-critical .v,
.facts-grid .row.sev-high .v { color: var(--critical-fg); }

/* Chart cards */
.chart-card {
  background: var(--surface); border-radius: 10px; box-shadow: var(--shadow);
  padding: 1.4rem 1.4rem 1rem; margin: 0.4rem 0 1.6rem;
}
.chart-card .chart { display: flex; justify-content: center; }
.chart-card .chart svg { display: block; max-width: 100%; height: auto; }
.chart-card figcaption {
  margin-top: 0.6rem; font-family: var(--sans); font-size: 0.86rem; color: var(--muted);
  text-align: center;
}

/* SWOT */
.swot {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
  margin: 0.6rem 0 1.4rem;
}
.swot .quad {
  background: var(--surface); border-radius: 10px; box-shadow: var(--shadow);
  padding: 1rem 1.1rem;
}
.swot .quad h4 { margin: 0 0 0.4rem; color: var(--accent); }
.swot ul { margin: 0; padding-left: 1.1rem; }
.swot li { margin: 0.3rem 0; }

/* Day-N */
.day-n { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 0.6rem 0 1.4rem; }
.day-n .card { background: var(--surface); border-radius: 10px; box-shadow: var(--shadow); padding: 1rem 1.1rem; }
.day-n .card h4 { color: var(--accent); margin-top: 0; }
.day-n ul { padding-left: 1.1rem; margin: 0.4rem 0 0; }
.day-n li { margin: 0.35rem 0; }

/* Recommendation ladder */
.options {
  display: grid; gap: 0.6rem; margin: 0.4rem 0 1.4rem;
}
.options .option {
  display: grid; grid-template-columns: auto 1fr auto; align-items: start;
  gap: 0.6rem 1.1rem;
  background: var(--surface); border-radius: 10px; box-shadow: var(--shadow);
  padding: 0.85rem 1.1rem;
}
.options .option .when { font-family: var(--sans); font-size: 0.92rem; color: #2c303a; }
.options .option .target {
  font-family: var(--sans); font-size: 0.86rem; color: var(--muted); white-space: nowrap;
}
.must-close {
  background: var(--critical-bg); color: var(--critical-fg);
  border-radius: 10px; padding: 0.9rem 1.1rem; margin: 0.6rem 0 1.4rem;
}
.must-close h4 { color: var(--critical-fg); margin-top: 0; }
.must-close ul { margin: 0.2rem 0 0; padding-left: 1.1rem; }

/* Claims evaluation */
.claims-table { width: 100%; border-collapse: collapse; margin: 0.5rem 0 1.4rem; font-family: var(--sans); font-size: 0.94rem; }
.claims-table th, .claims-table td { padding: 0.55rem 0.6rem; vertical-align: top; }
.claims-table thead th { text-align: left; border-bottom: 1px solid var(--rule-strong); color: var(--muted); font-weight: 600; }
.claims-table tbody tr { border-bottom: 1px solid var(--rule); }
.claims-table .status-pill {
  display: inline-block; padding: 0.18rem 0.6rem; border-radius: 999px;
  font-size: 0.78rem; letter-spacing: 0.02em; font-weight: 600;
}
.status-substantiated  { background: var(--pass-bg); color: var(--pass-fg); }
.status-partial        { background: var(--conditional-bg); color: var(--conditional-fg); }
.status-unsubstantiated{ background: var(--medium-bg); color: var(--medium-fg); }
.status-contradicted   { background: var(--critical-bg); color: var(--critical-fg); }

/* Remediation / debt table */
.tasks-table { width: 100%; border-collapse: collapse; margin: 0.5rem 0 1.6rem; font-family: var(--sans); font-size: 0.92rem; }
.tasks-table th, .tasks-table td { padding: 0.55rem 0.6rem; vertical-align: top; }
.tasks-table thead th { text-align: left; border-bottom: 1px solid var(--rule-strong); color: var(--muted); cursor: pointer; }
.tasks-table tbody tr { border-bottom: 1px solid var(--rule); }
.tasks-table code { font-family: var(--mono); font-size: 0.85em; }
.sev-pill {
  display: inline-block; padding: 0.12rem 0.55rem; border-radius: 999px;
  font-size: 0.74rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;
}
.sev-critical{ background: var(--critical-bg); color: var(--critical-fg); }
.sev-high    { background: var(--high-bg); color: var(--high-fg); }
.sev-medium  { background: var(--medium-bg); color: var(--medium-fg); }
.sev-low     { background: var(--low-bg); color: var(--low-fg); }
.sev-info    { background: var(--info-bg); color: var(--info-fg); }

/* Questions list */
.questions { padding-left: 1.4rem; }
.questions li { margin: 0.35rem 0; }

/* Persona narrative blocks (rendered late in the doc) */
.persona-block { background: var(--surface); border-radius: 10px; box-shadow: var(--shadow); padding: 1rem 1.2rem; margin: 0.6rem 0 1rem; }
.persona-block .summary { color: #2c303a; }

/* Both-narrator side-by-side */
.both-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 0.4rem 0 1.4rem; }
.both-grid .col { background: var(--surface); border-radius: 10px; box-shadow: var(--shadow); padding: 1rem 1.1rem; }
.both-grid .col h4 { margin-top: 0; color: var(--accent); }

/* 0.11.0 depth pass: exec summary, methodology, decomposition, gap, glossary, citations */
.exec-summary {
  background: var(--surface); border-left: 3px solid var(--accent);
  padding: 1.4rem 1.8rem; margin: 0.6rem 0 2.2rem;
  font-size: 1.06rem; line-height: 1.65; max-width: 72ch;
}
.exec-summary h2 { border-top: none; margin-top: 0; padding-top: 0; }
.exec-summary p { margin: 0.5rem 0 1.05rem; }
sup.cite { font-family: var(--sans); font-size: 0.7em; vertical-align: super; line-height: 1; }
sup.cite a { color: var(--accent); text-decoration: none; padding: 0 0.1em; }
sup.cite a:hover { text-decoration: underline; }

.methodology, .score-decomposition, .gap-analysis, .glossary, .citations {
  background: var(--surface); border-radius: 10px; box-shadow: var(--shadow);
  padding: 1.4rem 1.6rem; margin: 0.6rem 0 1.6rem;
}
.methodology h2, .score-decomposition h2, .gap-analysis h2, .glossary h2, .citations h2 {
  border-top: none; margin-top: 0; padding-top: 0;
}
.methodology h4 { margin: 1rem 0 0.4rem; color: var(--accent); font-size: 0.9rem; text-transform: none; letter-spacing: 0; }
.methodology pre.formula {
  background: var(--bg); border-radius: 6px; padding: 0.7rem 0.9rem;
  overflow-x: auto; font-size: 0.86rem; margin: 0.5rem 0 0.8rem;
}
.methodology pre.formula code { font-family: var(--mono); white-space: pre; }
.methodology summary { cursor: pointer; color: var(--accent); font-family: var(--sans); font-weight: 600; }
.methodology-table { width: 100%; border-collapse: collapse; font-family: var(--sans); font-size: 0.92rem; margin: 0.6rem 0; }
.methodology-table th, .methodology-table td { padding: 0.5rem 0.6rem; vertical-align: top; text-align: left; }
.methodology-table thead th { border-bottom: 1px solid var(--rule-strong); color: var(--muted); }
.methodology-table tbody tr { border-bottom: 1px solid var(--rule); }

.decomp-table, .phase-table {
  width: 100%; border-collapse: collapse;
  font-family: var(--sans); font-size: 0.92rem; margin: 0.6rem 0 1rem;
}
.decomp-table th, .decomp-table td, .phase-table th, .phase-table td { padding: 0.55rem 0.65rem; vertical-align: top; }
.decomp-table thead th, .phase-table thead th { text-align: left; border-bottom: 1px solid var(--rule-strong); color: var(--muted); }
.decomp-table tbody tr, .phase-table tbody tr { border-bottom: 1px solid var(--rule); }
.decomp-table code, .phase-table code { font-family: var(--mono); font-size: 0.85em; }
.muted { color: var(--muted); }

.gap-strip {
  display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;
  margin: 0.4rem 0 1rem;
}
.gap-strip > div {
  background: var(--bg); border-radius: 999px;
  padding: 0.45rem 0.95rem; font-family: var(--sans); font-size: 0.94rem;
}
.gap-strip .gap-current { background: var(--accent-soft); color: var(--accent); }
.gap-strip .gap-arrow { background: transparent; padding: 0.1rem; color: var(--muted); }
.gap-strip .gap-cleared { background: var(--pass-bg); color: var(--pass-fg); padding: 0.55rem 1rem; }

.glossary-list dt {
  font-family: var(--sans); font-weight: 700; color: var(--accent);
  margin-top: 1rem; font-size: 0.96rem;
}
.glossary-list dd { margin: 0.25rem 0 0.4rem; }
.glossary-list dd p { margin: 0.2rem 0; }
.glossary-list code { font-family: var(--mono); font-size: 0.84em; }

.citation-list { padding-left: 1.4rem; font-size: 0.94rem; }
.citation-list li { margin: 0.5rem 0; }
.citation-list ul.refs, .citation-list ul.sources {
  margin: 0.25rem 0 0.5rem 0.6rem; padding-left: 1rem;
  list-style: square; color: var(--muted);
}
.citation-list code { font-family: var(--mono); font-size: 0.84em; color: var(--ink); }

/* Print: collapse details, compact methodology */
@media print {
  .methodology details { all: revert; }
  .methodology details > summary { display: none; }
  .exec-summary { box-shadow: none; }
}

/* Engineering appendix */
.appendix-toggle { margin: 2.5rem 0 0; }
.appendix {
  background: var(--surface); border: 1px solid var(--rule); border-radius: 10px;
  padding: 1.2rem 1.4rem; margin-top: 0.6rem;
}
.appendix summary { cursor: pointer; font-family: var(--sans); font-weight: 600; color: var(--accent); }
.appendix .findings-table { width: 100%; border-collapse: collapse; font-family: var(--sans); font-size: 0.9rem; }
.appendix .findings-table th, .appendix .findings-table td { padding: 0.5rem 0.55rem; text-align: left; vertical-align: top; }
.appendix .findings-table thead th { border-bottom: 1px solid var(--rule-strong); color: var(--muted); }
.appendix .findings-table tbody tr { border-bottom: 1px solid var(--rule); }

/* Footer */
.doc-footer { margin-top: 3rem; font-family: var(--sans); font-size: 0.82rem; color: var(--muted); }

/* Print */
@media print {
  body { background: white; font-size: 11pt; }
  .doc { padding: 0.6cm 1.4cm; max-width: 100%; }
  .recommendation, .chart-card, .options .option, .swot .quad,
  .day-n .card, .both-grid .col, .appendix { box-shadow: none; border: 1px solid var(--rule); }
  h2 { page-break-after: avoid; }
  section, .chart-card, .swot .quad, .day-n .card, .options .option { page-break-inside: avoid; }
  .appendix[open] { page-break-before: always; }
}

@media (max-width: 760px) {
  .doc { padding: 1.5rem 1.1rem 3rem; }
  .cover { grid-template-columns: 1fr; }
  .swot, .day-n, .both-grid { grid-template-columns: 1fr; }
}
"""

_SORT_SCRIPT = """
document.querySelectorAll('table.sortable').forEach(function(t) {
  t.querySelectorAll('thead th').forEach(function(th, idx) {
    th.addEventListener('click', function() {
      var rows = Array.from(t.querySelectorAll('tbody tr'));
      var current = th.getAttribute('aria-sort');
      var next = current === 'ascending' ? 'descending' : 'ascending';
      t.querySelectorAll('thead th').forEach(function(o) { o.removeAttribute('aria-sort'); });
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
    if value is None:
        return ""
    return _html.escape(str(value), quote=True)


def _verdict_label(verdict: str) -> str:
    return _VERDICT_LABEL.get(verdict, verdict.replace("_", " ").title())


def _resolve_use_case_profile(use_case: str | None) -> dict | None:
    if not use_case:
        return None
    try:
        all_profiles = load_use_case_profiles()
    except Exception:
        return None
    profile = all_profiles.get(use_case) or None
    if profile is not None:
        # Inject the use_case key so dispatchers can read it back.
        profile = {**profile, "use_case": use_case}
    return profile


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------


def _render_cover(deliverable: Deliverable, *, generated_at: str) -> str:
    cover = deliverable.cover
    facts_html = ""
    if cover.headline_facts:
        cells = "".join(
            f'<div class="fact"><div class="k">{_esc(k)}</div><div class="v">{_esc(v)}</div></div>'
            for k, v in cover.headline_facts
        )
        facts_html = f'<div class="headline-facts">{cells}</div>'

    classification_html = ""
    if cover.classification_line:
        classification_html = (
            f'<div class="classification">{_esc(cover.classification_line)}</div>'
        )

    return f"""
<header class="cover">
  <div class="meta-block">
    <div class="meta">{_esc(deliverable.use_case.replace('_', ' ').upper())} · {_esc(generated_at)}</div>
    <h1 class="title">{_esc(cover.title)}</h1>
    <div class="subtitle">{_esc(cover.subtitle)}</div>
    {classification_html}
  </div>
  <div class="gauge" aria-label="Score gauge">{cover.score_gauge_svg}</div>
</header>
{_render_recommendation_pill(cover.recommendation, cover.recommendation_rationale)}
{facts_html}
"""


def _render_recommendation_pill(recommendation: str, rationale: str) -> str:
    return f"""
<div class="recommendation">
  <span class="pill pill-{_esc(recommendation)}">{_esc(_verdict_label(recommendation))}</span>
  <div class="rationale">{_esc(rationale)}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Section dispatch
# ---------------------------------------------------------------------------


def _render_section(section, *, narrator: str = "deterministic") -> str:
    kind = section.kind
    body = ""
    if kind == "prose":
        body = _render_prose(section)
    elif kind == "facts":
        body = _render_facts(section)
    elif kind == "chart":
        body = _render_chart(section)
    elif kind == "swot":
        body = _render_swot(section)
    elif kind == "day_n":
        body = _render_day_n(section)
    elif kind == "options_ladder":
        body = _render_options(section.data.get("options", []))
    elif kind == "questions":
        body = _render_questions(section)
    elif kind == "claims_evaluation":
        body = _render_claims(section)
    elif kind == "remediation_table":
        body = _render_tasks_table(section)
    else:
        body = _render_prose(section)

    summary_html = (
        f'<p class="summary">{_esc(section.summary)}</p>' if section.summary else ""
    )

    return f"""
<section class="kind-{_esc(kind)}">
  <h2>{_esc(section.title)}</h2>
  {summary_html}
  {body}
</section>
"""


def _render_prose(section) -> str:
    paragraphs = section.data.get("paragraphs") or []
    out: list[str] = []
    for para in paragraphs:
        if isinstance(para, str) and para.startswith("`"):
            # Treat backtick-prefixed lines as a code-style list item.
            out.append(f'<p><code>{_esc(para)}</code></p>')
        else:
            out.append(f"<p>{_esc(para)}</p>")
    if not out and section.narrative_block:
        out.append(f"<p>{_esc(section.narrative_block.summary)}</p>")
    return "\n".join(out)


def _render_facts(section) -> str:
    rows: list[str] = []
    for fact in section.facts:
        sev_class = f" sev-{_esc(fact.severity)}" if fact.severity else ""
        note_html = f'<div class="note">{_esc(fact.note)}</div>' if fact.note else ""
        rows.append(
            f'<div class="row{sev_class}"><div class="k">{_esc(fact.label)}</div>'
            f'<div class="v">{_esc(fact.value)}</div>{note_html}</div>'
        )
    grid = f'<div class="facts-grid">{"".join(rows)}</div>' if rows else ""

    paragraphs_html = ""
    paragraphs = section.data.get("paragraphs") or []
    if paragraphs:
        paragraphs_html = "".join(f"<p>{_esc(p)}</p>" for p in paragraphs)
    return f"{grid}{paragraphs_html}"


def _render_chart(section) -> str:
    if not section.chart_svg:
        return '<p class="muted">Chart unavailable.</p>'
    caption = section.summary or ""
    return f"""
<figure class="chart-card">
  <div class="chart">{section.chart_svg}</div>
  <figcaption>{_esc(caption)}</figcaption>
</figure>
"""


def _render_swot(section) -> str:
    quadrants = [
        ("Strengths", section.data.get("strengths", [])),
        ("Weaknesses", section.data.get("weaknesses", [])),
        ("Opportunities", section.data.get("opportunities", [])),
        ("Threats", section.data.get("threats", [])),
    ]
    out: list[str] = []
    for title, items in quadrants:
        list_items = "".join(f"<li>{_esc(item)}</li>" for item in items)
        out.append(
            f'<div class="quad"><h4>{_esc(title)}</h4><ul>{list_items}</ul></div>'
        )
    return f'<div class="swot">{"".join(out)}</div>'


def _render_day_n(section) -> str:
    columns = [
        ("Day 30", section.data.get("day_30", [])),
        ("Day 60", section.data.get("day_60", [])),
        ("Day 90", section.data.get("day_90", [])),
    ]
    out: list[str] = []
    for title, items in columns:
        items_html = "".join(f"<li>{_esc(item)}</li>" for item in items)
        out.append(
            f'<div class="card"><h4>{_esc(title)}</h4><ul>{items_html}</ul></div>'
        )
    return f'<div class="day-n">{"".join(out)}</div>'


def _render_questions(section) -> str:
    questions = section.data.get("questions") or []
    items = "".join(f"<li>{_esc(q)}</li>" for q in questions)
    return f'<ol class="questions">{items}</ol>'


def _render_claims(section) -> str:
    claims = section.data.get("claims") or []
    overclaim = section.data.get("overclaim_callouts") or []
    rows: list[str] = []
    for c in claims:
        status = (c.get("evidence_status") or "partial").lower()
        rows.append(
            f"<tr>"
            f"<td>{_esc(c.get('claim', ''))}</td>"
            f'<td><span class="status-pill status-{_esc(status)}">{_esc(status)}</span></td>'
            f"<td>{_esc(c.get('evidence_text', ''))}</td>"
            f"</tr>"
        )
    callouts_html = ""
    if overclaim:
        bullet_html = "".join(f"<li>{_esc(o)}</li>" for o in overclaim)
        callouts_html = (
            f'<div class="must-close"><h4>Overclaim signals</h4><ul>{bullet_html}</ul></div>'
        )
    return (
        '<table class="claims-table"><thead><tr>'
        '<th>Pitch claim</th><th>Status</th><th>Evidence</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        f'{callouts_html}'
    )


def _render_tasks_table(section) -> str:
    tasks = section.data.get("tasks") or []
    rows: list[str] = []
    for t in tasks:
        sev = str(t.get("severity") or t.get("priority") or "").lower()
        sev_pill = (
            f'<span class="sev-pill sev-{_esc(sev)}">{_esc(sev)}</span>' if sev else ""
        )
        steps = t.get("implementation_steps") or []
        steps_html = (
            "<ul>" + "".join(f"<li>{_esc(s)}</li>" for s in steps[:3]) + "</ul>"
            if steps
            else ""
        )
        cmds = t.get("verification_commands") or []
        cmds_html = (
            "<ul>" + "".join(f"<li><code>{_esc(c)}</code></li>" for c in cmds[:3]) + "</ul>"
            if cmds
            else ""
        )
        target_paths = t.get("target_paths") or []
        paths_html = (
            "<ul>" + "".join(f"<li><code>{_esc(p)}</code></li>" for p in target_paths[:3]) + "</ul>"
            if target_paths
            else (
                "".join(f"<div><code>{_esc(e)}</code></div>" for e in t.get("evidence", [])[:3])
                if t.get("evidence")
                else ""
            )
        )
        delta = t.get("expected_score_delta")
        delta_text = f"+{float(delta):.1f}" if delta else "—"
        effort = t.get("effort", "—")
        title = t.get("title") or t.get("statement") or t.get("subcategory") or t.get("id") or "task"
        rows.append(
            f"<tr>"
            f"<td>{sev_pill}</td>"
            f"<td><strong>{_esc(title)}</strong>"
            f'{("<div class=\"muted\">" + _esc(t.get("statement", "")) + "</div>") if t.get("statement") else ""}</td>'
            f"<td>{paths_html}</td>"
            f"<td>{steps_html}{cmds_html}</td>"
            f'<td data-sort="{_esc(effort)}">{_esc(effort)}</td>'
            f'<td data-sort="{_esc(delta or 0)}">{_esc(delta_text)}</td>'
            f"</tr>"
        )
    return (
        '<table class="tasks-table sortable"><thead><tr>'
        "<th>Severity</th><th>Title</th><th>Targets</th><th>Steps · Verification</th><th>Effort</th><th>Δ score</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _render_options(options: list[dict | RecommendationOption]) -> str:
    rows: list[str] = []
    for opt in options:
        if isinstance(opt, RecommendationOption):
            verdict = opt.verdict
            condition = opt.condition
            target = opt.expected_score_after
            rationale = opt.rationale
        else:
            verdict = opt.get("verdict", "")
            condition = opt.get("condition", "")
            target = opt.get("expected_score_after")
            rationale = opt.get("rationale", "")
        target_html = f"→ {int(target)}/100" if target is not None else "—"
        rows.append(
            f'<div class="option">'
            f'<span class="pill pill-{_esc(verdict)}">{_esc(_verdict_label(verdict))}</span>'
            f'<div class="when"><strong>If:</strong> {_esc(condition)}'
            f'<div class="rationale">{_esc(rationale)}</div></div>'
            f'<div class="target">{_esc(target_html)}</div>'
            f"</div>"
        )
    return f'<div class="options">{"".join(rows)}</div>'


def _render_recommendation_block(deliverable: Deliverable) -> str:
    rec = deliverable.recommendation
    if rec is None:
        return ""
    must_close_html = ""
    if rec.must_close_before_proceeding:
        items = "".join(f"<li>{_esc(item)}</li>" for item in rec.must_close_before_proceeding)
        must_close_html = (
            f'<div class="must-close"><h4>Must close before proceeding</h4>'
            f'<ul>{items}</ul></div>'
        )
    options_html = _render_options(rec.options)
    return f"""
<section class="kind-recommendation">
  <h2>Recommendation</h2>
  <p class="lede">{_esc(rec.headline)}</p>
  {options_html}
  {must_close_html}
</section>
"""


# ---------------------------------------------------------------------------
# Engineering appendix (the v0.9.0 finding list, collapsed)
# ---------------------------------------------------------------------------


def _render_appendix(scored: dict, deliverable: Deliverable) -> str:
    findings = scored.get("findings") or []
    production: list[dict] = []
    fixture: list[dict] = []
    for f in findings:
        if is_fixture_finding(f):
            fixture.append(f)
        else:
            production.append(f)

    def _row(f: dict) -> str:
        sev = (f.get("severity") or "info").lower()
        evidence = f.get("evidence") or []
        loc = ""
        if evidence:
            e = evidence[0]
            loc = f"{e.get('path', '?')}:{e.get('line_start', '?')}"
        return (
            f"<tr>"
            f'<td><span class="sev-pill sev-{_esc(sev)}">{_esc(sev)}</span></td>'
            f"<td>{_esc((f.get('subcategory') or '').replace('_', ' ').title())}</td>"
            f"<td>{_esc(f.get('statement', ''))}</td>"
            f"<td><code>{_esc(loc)}</code></td>"
            f"</tr>"
        )

    def _table(rows: list[dict], title: str) -> str:
        if not rows:
            return ""
        rows_sorted = sorted(rows, key=lambda f: _SEVERITY_ORDER.get((f.get("severity") or "low").lower(), 9))
        body = "".join(_row(f) for f in rows_sorted)
        return f"""
<details open>
  <summary>{_esc(title)} ({len(rows)})</summary>
  <table class="findings-table"><thead><tr>
    <th>Severity</th><th>Subcategory</th><th>Statement</th><th>Where</th>
  </tr></thead><tbody>{body}</tbody></table>
</details>
"""

    cats = (scored.get("scoring") or {}).get("category_scores") or []
    if isinstance(cats, list):
        cat_rows = "".join(
            f"<tr>"
            f"<td>{_esc(c.get('category', '').replace('_', ' ').title())}</td>"
            f"<td>{_esc(c.get('score', 0))} / {_esc(c.get('max_score', 0))}</td>"
            f"<td>{_esc('yes' if c.get('applicable', True) else 'no')}</td>"
            f"<td>{_esc(c.get('summary', ''))}</td>"
            f"</tr>"
            for c in cats
            if isinstance(c, dict)
        )
        cat_table = f"""
<details open>
  <summary>Category scores ({len(cats)})</summary>
  <table class="findings-table"><thead><tr>
    <th>Category</th><th>Score</th><th>Applicable</th><th>Summary</th>
  </tr></thead><tbody>{cat_rows}</tbody></table>
</details>
"""
    else:
        cat_table = ""

    return f"""
<section class="appendix-toggle">
  <details class="appendix">
    <summary>Engineering appendix — full evidence ({len(production)} production · {len(fixture)} fixture)</summary>
    {cat_table}
    {_table(production, 'Production findings')}
    {_table(fixture, 'Fixture / non-production findings')}
  </details>
</section>
"""


# ---------------------------------------------------------------------------
# Persona narrative blocks rendered after the structured sections
# ---------------------------------------------------------------------------


def _render_persona_blocks(deliverable: Deliverable, *, narrator: str) -> str:
    """Already part of `deliverable.sections` for the four shipped builders.

    This is a hook for the dual-narrator mode: when ``narrator == "both"``,
    each persona block is rendered with side-by-side deterministic + LLM
    columns. The deterministic column comes from the existing summary; the
    LLM column comes from ``deliverable.persona_blocks_llm`` if populated
    upstream (otherwise we fall back to deterministic alone).
    """
    return ""  # placeholder — sections already include the narrative blocks


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def _render_executive_summary(deliverable: Deliverable) -> str:
    """0.11.0 depth pass: prose exec summary with inline footnote markers."""
    if not deliverable.executive_summary:
        return ""
    paragraphs = "".join(
        f"<p>{_render_inline_citations(p)}</p>"
        for p in deliverable.executive_summary
    )
    return f"""
<section class="exec-summary" aria-label="Executive summary">
  <h2>Executive summary</h2>
  {paragraphs}
</section>
"""


def _render_inline_citations(text: str) -> str:
    """Replace ``[N]`` markers with superscript footnote anchors.

    The exec-summary builder emits raw ``[N]`` tokens; this turns them
    into clickable ``<sup class="cite"><a href="#cite-N">[N]</a></sup>``
    while leaving real bracketed text alone (e.g. "[draft]") via a
    digits-only match.
    """
    import re as _re

    # First escape the text, then unescape only the citation markers.
    escaped = _esc(text)
    # Markdown-style **bold** → <strong> for the prose paragraphs.
    escaped = _re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return _re.sub(
        r"\[(\d+)\]",
        r'<sup class="cite"><a href="#cite-\1">[\1]</a></sup>',
        escaped,
    )


def _render_methodology(deliverable: Deliverable) -> str:
    """Methodology box: formula, threshold explanation, multipliers, verdict rules."""
    m = deliverable.methodology
    if m is None:
        return ""

    rule_rows = "".join(
        f"<tr><td><code>{_esc(r['verdict'])}</code></td>"
        f"<td>{_esc(r['condition'])}</td>"
        f"<td><code>{_esc(r['source'])}</code></td></tr>"
        for r in m.verdict_rule_table
    )

    calibration_html = (
        f'<p class="muted"><em>{_esc(m.calibration_band)}</em></p>'
        if m.calibration_band
        else ""
    )

    return f"""
<section class="methodology" id="methodology" aria-label="Methodology">
  <h2>Methodology</h2>
  <details open>
    <summary>How the score and verdict were computed</summary>
    <h4>Score formula</h4>
    <pre class="formula"><code>{_esc(m.score_formula)}</code></pre>
    <h4>Threshold</h4>
    <p>{_esc(m.threshold_explanation)}</p>
    <h4>Multipliers</h4>
    <p>{_esc(m.multiplier_explanation)}</p>
    <h4>Verdict rules</h4>
    <table class="methodology-table">
      <thead><tr><th>Verdict</th><th>Condition</th><th>Source</th></tr></thead>
      <tbody>{rule_rows}</tbody>
    </table>
    {calibration_html}
  </details>
</section>
"""


def _render_score_decomposition(deliverable: Deliverable) -> str:
    """Two-column arithmetic: per-category breakdown + global penalties."""
    decomp = deliverable.score_decomposition
    if decomp is None:
        return ""

    rows = []
    for c in decomp.categories:
        if c.applicability != "applicable":
            applicability_cell = '<span class="muted">n/a</span>'
            arithmetic = '<span class="muted">excluded</span>'
        else:
            applicability_cell = "applicable"
            top_dedux = "; ".join(
                f"{d.get('finding_id', '?')} −{d['deduction']:.1f}"
                for d in c.deductions[:3]
            ) or "—"
            arithmetic = (
                f"<code>base {c.base_max} × mult {c.multiplier:.2f}</code> "
                f"→ weight {c.normalized_weight}/100; "
                f"<strong>earned {c.earned:.1f}</strong>; "
                f"top deductions: {_esc(top_dedux)}"
            )
        rows.append(
            f"<tr><td>{_esc(c.label)}</td>"
            f"<td>{applicability_cell}</td>"
            f"<td>{arithmetic}</td></tr>"
        )

    flat_rows = ""
    if decomp.flat_penalties:
        items = "".join(
            f"<li><code>{_esc(name)}</code>: −{val} pts</li>"
            for name, val in decomp.flat_penalties
        )
        flat_rows = f"<h4>Flat penalties (production maturity)</h4><ul>{items}</ul>"

    return f"""
<section class="score-decomposition" id="score-decomposition" aria-label="Score decomposition">
  <h2>Score decomposition</h2>
  <p class="summary">
    The score arithmetic, decomposed per category. <code>earned = max(0, weight − Σ deductions)</code>;
    each deduction is <code>severity_weight × confidence_multiplier × maturity_factor × magnitude/10</code>.
  </p>
  <table class="decomp-table">
    <thead><tr><th>Category</th><th>Applicability</th><th>Arithmetic</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  {flat_rows}
  <p class="muted"><em>{_esc(decomp.score_confidence_rationale)}</em></p>
</section>
"""


def _render_gap_analysis(deliverable: Deliverable) -> str:
    gap = deliverable.gap
    decomp = deliverable.score_decomposition
    if gap is None or decomp is None:
        return ""

    if gap.gap_to_pass <= 0:
        gap_strip = (
            f'<div class="gap-cleared">Score {decomp.overall} clears the '
            f'pass threshold of {decomp.pass_threshold}; '
            f'distinction sits {gap.gap_to_distinction} points above current.</div>'
        )
    else:
        gap_strip = (
            f'<div class="gap-current">Current <strong>{decomp.overall}</strong></div>'
            f'<div class="gap-arrow">→</div>'
            f'<div class="gap-target">Pass <strong>{decomp.pass_threshold}</strong> '
            f'(gap <strong>{gap.gap_to_pass}</strong>)</div>'
            f'<div class="gap-arrow">→</div>'
            f'<div class="gap-target">Distinction <strong>{decomp.distinction_threshold}</strong> '
            f'(gap <strong>{gap.gap_to_distinction}</strong>)</div>'
        )

    if gap.closing_phases:
        phase_rows = "".join(
            f"<tr><td><code>{_esc(p['phase'])}</code></td>"
            f"<td>{p['task_count']} task(s)</td>"
            f"<td>+{p['projected_lift']:.1f}</td>"
            f"<td>{p['before']:.1f} → <strong>{p['after']:.1f}</strong></td>"
            f"<td>{'✓ clears pass' if p['clears'] else '—'}</td></tr>"
            for p in gap.closing_phases
        )
        phase_table = f"""
<h4>Phases that close the gap</h4>
<p class="muted"><em>Per-phase deltas are scoring-engine projections from
<code>sdlc_assessor/remediation/planner.py</code>, not measurements against
historical outcomes. Real deltas may differ; outcome-calibrated projections
arrive in 0.14.0.</em></p>
<table class="phase-table">
  <thead><tr><th>Phase</th><th>Tasks</th><th>Projected lift</th><th>Score before → after</th><th>Pass?</th></tr></thead>
  <tbody>{phase_rows}</tbody>
</table>
"""
    else:
        phase_table = (
            '<p class="muted">No remediation plan was attached to this run; '
            "per-phase projections unavailable.</p>"
        )

    return f"""
<section class="gap-analysis" id="gap-analysis" aria-label="Gap analysis">
  <h2>Gap analysis</h2>
  <div class="gap-strip">{gap_strip}</div>
  {phase_table}
</section>
"""


def _render_glossary(deliverable: Deliverable) -> str:
    if not deliverable.glossary:
        return ""
    items = "".join(
        f'<dt id="glossary-{_esc(e.term).replace(" ", "-")}">{_esc(e.term)}</dt>'
        f'<dd><p>{_esc(e.long_def)}</p>'
        f'<p class="muted">Sources: {", ".join(f"<code>{_esc(s)}</code>" for s in e.sources)}</p></dd>'
        for e in deliverable.glossary
    )
    return f"""
<section class="glossary" id="glossary" aria-label="Glossary">
  <h2>Glossary</h2>
  <p class="summary">
    Every term used in this report that depends on a value in the codebase.
    Each entry cites the path where the term is actually defined.
  </p>
  <dl class="glossary-list">{items}</dl>
</section>
"""


def _render_citations(deliverable: Deliverable) -> str:
    if not deliverable.citations:
        return ""
    items = []
    for idx, c in enumerate(deliverable.citations, start=1):
        refs = "".join(f"<li><code>{_esc(r)}</code></li>" for r in c.evidence_refs)
        sources = "".join(
            f"<li><code>{_esc(path)}{':' + str(line) if line else ''}</code></li>"
            for path, line in c.source_files
        )
        items.append(
            f'<li id="cite-{idx}">'
            f'<strong>[{idx}]</strong> {_esc(c.text)}'
            f'{f"<ul class=\"refs\">{refs}</ul>" if refs else ""}'
            f'{f"<ul class=\"sources\">{sources}</ul>" if sources else ""}'
            "</li>"
        )
    return f"""
<section class="citations" id="citations" aria-label="Citations">
  <h2>Citations</h2>
  <ol class="citation-list">{''.join(items)}</ol>
</section>
"""


def render_deliverable_html(
    deliverable: Deliverable,
    *,
    scored: dict,
    narrator: str = "deterministic",
    title: str | None = None,
) -> str:
    """Render a :class:`Deliverable` as a stand-alone HTML document.

    ``narrator`` is reflected in the rendered prose (the LLM column in
    ``both`` mode). The dual-narrator wiring lives in
    :mod:`sdlc_assessor.narrator` — this renderer just consumes whatever
    text is already attached to the deliverable.

    Document order (0.11.0):

    1. Cover (existing)
    2. Executive summary (NEW — prose with inline footnote markers)
    3. Methodology (NEW — formula + threshold + multipliers + verdict rules)
    4. Score decomposition (NEW — per-category arithmetic)
    5. Gap analysis (NEW — gap-to-pass + closing phases as projections)
    6. Body sections (existing — radar, risk matrix, persona narrative blocks)
    7. Recommendation block (existing)
    8. Glossary (NEW)
    9. Citations (NEW)
    10. Engineering appendix (existing — finding listings)
    11. Footer
    """
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    cover_html = _render_cover(deliverable, generated_at=generated_at)
    exec_summary_html = _render_executive_summary(deliverable)
    methodology_html = _render_methodology(deliverable)
    decomp_html = _render_score_decomposition(deliverable)
    gap_html = _render_gap_analysis(deliverable)
    sections_html = "\n".join(
        _render_section(section, narrator=narrator) for section in deliverable.sections
    )
    recommendation_html = _render_recommendation_block(deliverable)
    glossary_html = _render_glossary(deliverable)
    citations_html = _render_citations(deliverable)
    appendix_html = _render_appendix(scored, deliverable)

    page_title = title or f"{deliverable.cover.title} — {deliverable.use_case.replace('_', ' ').title()}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(page_title)}</title>
  <style>{_STYLESHEET}</style>
</head>
<body>
  <main class="doc">
    {cover_html}
    {exec_summary_html}
    {methodology_html}
    {decomp_html}
    {gap_html}
    {sections_html}
    {recommendation_html}
    {glossary_html}
    {citations_html}
    {appendix_html}
    <footer class="doc-footer">
      Generated by sdlc-assessor · {_esc(generated_at)} · narrator: {_esc(narrator)}.
    </footer>
  </main>
  <script>{_SORT_SCRIPT}</script>
</body>
</html>
"""


def render_html_report(
    scored: dict,
    *,
    narrator: str = "deterministic",
    title: str | None = None,
) -> str:
    """Top-level HTML renderer used by the CLI ``render`` and ``run`` commands.

    Resolves the use-case profile from ``scored.scoring.effective_profile``
    and routes to the persona-distinct deliverable builder. Falls back to
    the generic deliverable shape when the use-case is unknown.
    """
    use_case = (
        ((scored.get("scoring") or {}).get("effective_profile") or {}).get("use_case")
        or "engineering_triage"
    )
    profile = _resolve_use_case_profile(use_case) or {"use_case": use_case}
    deliverable = build_deliverable(scored, profile)
    return render_deliverable_html(
        deliverable, scored=scored, narrator=narrator, title=title
    )


__all__ = [
    "render_deliverable_html",
    "render_html_report",
]
