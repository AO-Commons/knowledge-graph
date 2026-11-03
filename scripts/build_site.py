#!/usr/bin/env python3
"""Build the preview site: one page, search, and two doors into an issue.

    python3 scripts/build_site.py

What this is for. Somebody arrives from a paper or a link and wants to know
what the library holds, what it says about a record, and how to tell us we got
something wrong. That is the whole surface. It replaced a nine-tab application
on 2026-10-30 that also carried a review screen, an Add form, a classifier
index, a force-directed graph and the reader documentation — which is a lot of
page for a library of 363 records, and most of it was built for whoever
maintains the corpus rather than for whoever reads it.

Reviewing moved to the signed-in application, where an author can be invited to
judge claims about their own paper. Nothing here writes: both buttons open a
GitHub issue with the fields filled in, and the issue is the record of the ask.

The styling is AO Commons', copied from `src/shared/tokens.css` in the website
repository rather than imported, because a preview page should not fail to
render when a sibling repository moves a file. It takes the same selection
from it that the signed-in app does -- the application column, the application
end of the type scale, the "AO Commons | Knowledge Graph" lockup and the dark
footer -- so the preview and the app read as one surface rather than two.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

from ao_commons_kg.claims import load_claims  # noqa: E402
from ao_commons_kg.people import person_nodes  # noqa: E402
from ao_commons_kg.questions import load_questions  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

OUTPUT = REPO / "site" / "index.html"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
ISSUES = "https://github.com/AO-Commons/knowledge-graph/issues/new"

#: Kinds a reader filters by, mapped from `resource_type`. The taxonomy's own
#: vocabulary is finer than anybody browsing wants.
KIND = {
    "peer-reviewed-paper": "Paper", "preprint": "Paper", "paper": "Paper",
    "article": "Article", "report": "Report", "technical-report": "Report",
    "code-tool": "Tool", "tool": "Tool",
    "written-work": "Article",
    "platform": "Deployment", "deployment": "Deployment",
    "evaluation-suite": "Benchmark", "benchmark": "Benchmark",
    "research-programme": "Programme", "standard": "Standard",
}


CURATED = REPO / "data" / "curated.yml"


def curated_ids() -> set[str]:
    """The records a person put on the list, from data/curated.yml.

    The corpus is wide because a citation scan should be allowed to bring back
    work nobody has looked at yet. This is the part of it AO Commons stands
    behind, and the part the site opens on.
    """
    if not CURATED.exists():
        return set()
    doc = yaml.safe_load(CURATED.read_text(encoding="utf-8")) or {}
    ids = {r for stream in doc.get("streams") or [] for r in stream.get("records") or []}
    ids |= set((doc.get("build_page") or {}).get("records") or [])
    return ids


def payload() -> dict:
    resources = load_resources()
    curated = curated_ids()
    claims = list(load_claims())
    topics = {t.id.removeprefix("topic:"): t.title for t in load_taxonomy(TAXONOMY)}
    questions, edges = load_questions(claims=claims)

    by_resource: dict[str, list] = defaultdict(list)
    for claim in claims:
        by_resource[claim.resource_id].append(claim)

    # Which questions a record bears on, through the gap claims it carries.
    asks: dict[str, set[str]] = defaultdict(set)
    claim_home = {c.id: c.resource_id for c in claims}
    for edge in edges:
        home = claim_home.get(edge.source_id)
        if home:
            asks[home].add(edge.target_id)

    records = []
    for r in resources:
        mine = by_resource.get(r.id, [])
        records.append({
            "id": r.id,
            "title": r.title,
            "authors": r.authors or [],
            "year": (r.published_at or "")[:4],
            "url": r.url or (f"https://doi.org/{r.doi}" if r.doi else ""),
            "doi": r.doi or "",
            "kind": KIND.get(r.resource_type, r.resource_type.replace("-", " ").title()),
            "topics": r.taxonomy_topics or [],
            "orgs": r.organizations or [],
            "role": r.role or "",
            "background": bool(r.is_borrowed_background),
            "curated": r.id in curated,
            "coverage": r.text_coverage,
            "blurb": clip(r.description or r.abstract or "", 420),
            "claims": [{
                "id": c.id, "text": c.text, "quote": c.quote,
                "kind": c.claim_type.value,
                "own": c.attribution.value == "own",
                "whose": c.attributed_to or "",
                "reviewed": bool(c.verdict),
            } for c in mine],
            "asks": sorted(asks.get(r.id, ())),
        })

    # Which papers ask each question, counted apart from how many claims do:
    # a question two papers ask is a claim about a field, one paper asking
    # twice is that paper's framing.
    asked: dict[str, dict] = {}
    for q in questions:
        claims_on = [e.source_id for e in edges if e.target_id == q.id]
        papers = sorted({claim_home[c] for c in claims_on if c in claim_home})
        asked[q.id] = {"text": q.text, "note": q.note or "",
                       "papers": papers, "occurrences": len(claims_on)}

    return {
        "built": __import__("datetime").date.today().isoformat(),
        "release": latest_release(),
        "asked": asked,
        "records": sorted(records, key=lambda r: (bool(r["claims"]), r["year"] or "0000"),
                          reverse=True),
        "topics": topics,

        "people": {p["name"]: p["records"] for p in people_index(resources)},
        "counts": {
            "records": len(resources),
            "curated": sum(1 for r in resources if r.id in curated),
            "claims": len(claims),
            "read": len(by_resource),
            "reviewed": sum(1 for c in claims if c.verdict),
            "questions": len(questions),
            "topics": len(topics),
        },
    }


def latest_release() -> str:
    """The newest release in `data/releases`, by version rather than by name.

    Named on the page because a build from a stale corpus looks identical to
    one from a fresh corpus, and the version is the only thing that tells
    them apart. Sorted numerically: a plain sort puts v0.9.0 after v0.12.0.
    """
    folder = REPO / "data" / "releases"
    if not folder.exists():
        return ""
    def version(path):
        return [int(n) for n in path.name.lstrip("v").split(".") if n.isdigit()]
    releases = sorted((p for p in folder.iterdir() if p.is_dir()), key=version)
    return releases[-1].name if releases else ""


def clip(text: str, limit: int) -> str:
    """Cut at a word, not mid-syllable. An abstract ending "to avoid sh" reads
    as a broken page rather than as a summary that had to stop."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:text.rfind(" ", 0, limit)].rstrip(" ,;:") + "…"


def people_index(resources) -> list[dict]:
    """Every author, and what else of theirs the library holds.

    Through `people.person_nodes` rather than by splitting bylines here, so a
    name folded one way on the site and another in the graph cannot happen.
    """
    from collections import defaultdict
    wrote: dict[str, list[str]] = defaultdict(list)
    known = {person.name for person in person_nodes(resources).values()}
    for record in resources:
        for name in record.authors or []:
            if name in known:
                wrote[name].append(record.id)
    return [{"name": name, "records": ids}
            for name, ids in sorted(wrote.items()) if len(ids) > 1]


def render(data: dict) -> str:
    # `</` inside a JSON string would close the script element early.
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__DATA__", blob).replace("__ISSUES__", ISSUES)


def main() -> int:
    data = payload()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(data), encoding="utf-8")
    size = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT.relative_to(REPO)}  {size:,} bytes")
    c = data["counts"]
    print(f"  {c['records']} records · {c['claims']} claims from {c['read']} read "
          f"· {c['reviewed']} reviewed · {c['questions']} questions")
    return 0


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AO Commons Knowledge Graph</title>
<meta name="description" content="A collection of research on autonomous organizations, where AI agents hold operational or decision-making authority. In preview: coverage is incomplete and most claims have not been checked by a person.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,500&family=Hanken+Grotesk:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap">
<style>
/* AO Commons tokens, copied from the website's src/shared/tokens.css, in the
   same selection the knowledge graph app takes: the application column and
   the application end of the type scale. Both surfaces read as one app. */
:root{
  --bg:#f5f8fb; --sky:#cfe4f7; --panel:#fff; --panel-2:#ebebe8;
  --ink:#1a1a19; --ink-2:#5a5a57; --ink-3:#8b8b86;
  --line:#d9d9d5; --line-2:#bdbdb8;
  --green:#0e4f46; --green-ink:#0a3c35; --green-bg:#dde9e6;
  --serif:"Bricolage Grotesque","Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --sans:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --mono:"DM Mono","SFMono-Regular",Menlo,monospace;
  /* type scale: a role is picked, a size is never invented */
  --t-section:clamp(32px,3.4vw,50px);
  --t-heading:clamp(24px,2.2vw,32px);
  --t-lede:clamp(22px,2.1vw,30px);
  --t-sub:clamp(18px,1.45vw,21px);
  --t-body:17px;
  --t-small:14.5px;
  --t-meta:12px;
  --t-row:clamp(17px,1.25vw,20px);
  --t-figure:clamp(28px,2.4vw,36px);
  /* layout: the app column, which keeps its share on a wide window */
  --gutter:clamp(20px,4vw,64px);
  --max:clamp(1360px,92vw,1680px);
  --wordmark:clamp(24px,2.2vw,32px);
  --radius:10px;
  color-scheme:light;
}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;flex-direction:column;
     background:linear-gradient(180deg,var(--sky) 0,var(--bg) 70vh) no-repeat,var(--bg);
     color:var(--ink);font-family:var(--sans);font-size:var(--t-body);line-height:1.6;
     -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
:focus-visible{outline:2px solid var(--green);outline-offset:2px}
.wrap{max-width:var(--max);margin:0 auto;padding-inline:var(--gutter)}

/* ---- header: "AO Commons | Knowledge Graph", the lockup the app uses ---- */
.top{padding-block:clamp(24px,3vw,40px) 0}
.top .wrap{display:grid;grid-template-columns:auto minmax(0,1fr);
           align-items:center;gap:clamp(20px,3vw,44px)}
.top__brand{justify-self:start;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.wordmark{font-family:var(--serif);font-size:var(--wordmark);font-weight:600;
          letter-spacing:-.03em;white-space:nowrap}
.top__what{font-family:var(--serif);font-size:var(--wordmark);font-weight:400;
           letter-spacing:-.03em;white-space:nowrap}
.top__rule{font-size:calc(var(--wordmark)*.92);font-weight:200;color:var(--line-2)}
.beta{display:inline-flex;align-items:center;padding:5px 12px 6px;border-radius:999px;
      background:var(--green);color:#fff;font-family:var(--mono);font-size:11px;
      font-weight:500;letter-spacing:.09em;text-transform:uppercase;white-space:nowrap}
.top__right{justify-self:end;display:flex;align-items:center;gap:10px;flex-wrap:wrap}

/* pill buttons, ink outline by default, green for the primary action */
.btn{display:inline-flex;align-items:center;gap:12px;padding:13px 22px;cursor:pointer;
     border:1.5px solid var(--ink);border-radius:999px;background:transparent;color:var(--ink);
     font-family:var(--serif);font-size:15px;font-weight:500;letter-spacing:-.01em;
     line-height:1;white-space:nowrap;
     transition:background .18s,color .18s,border-color .18s,transform .18s,box-shadow .18s}
.btn:hover{background:var(--ink);color:#fff;transform:translateY(-1px)}
.btn--green{background:var(--green);border-color:var(--green);color:#fff;
            box-shadow:0 10px 24px -12px rgba(14,79,70,.7)}
.btn--green:hover{background:var(--green-ink);border-color:var(--green-ink);
                  box-shadow:0 14px 28px -12px rgba(14,79,70,.8)}

/* ---- what this is, and how far along it is ---- */
/* Two columns, because one is a column of text six lines tall against an
   empty right half on anything wider than a laptop. Each caps at a measure
   you can still read; they stack below the app's own breakpoint. */
/* Room underneath, because the sticky bar follows immediately and the
   longer of the two columns was finishing a sentence against it. */
.intro{padding-block:clamp(18px,2.2vw,30px) clamp(26px,3vw,44px)}
/* Two columns pushed to the edges of the page, the way the header puts the
   wordmark at one end and the buttons at the other. Each caps at a measure
   you can read; the slack goes to the gutter between them rather than into
   one long line or a void on the right. */
.intro .wrap{display:grid;grid-template-columns:minmax(0,66ch) minmax(0,58ch);
             justify-content:space-between;gap:clamp(24px,3vw,64px);align-items:start}
.notice{margin:0;color:var(--ink-2)}
.intro__note p + p{margin-top:clamp(12px,1.2vw,18px)}
/* Each sentence of the opening starts its own row. A sentence that runs past
   the measure still wraps — what this sets is where one begins, not how long
   it is allowed to be. */
.intro__lead p + p{margin-top:.5em}
.notice--lead{font-size:var(--t-sub);line-height:1.5;color:var(--ink)}
@media (max-width:860px){.intro .wrap{grid-template-columns:minmax(0,66ch)}
                         .intro__note{margin-top:clamp(14px,1.6vw,22px)}}
.notice a{color:var(--green);border-bottom:1px solid var(--green-bg)}
.notice a:hover{border-color:var(--green)}
.notice .tag{vertical-align:1px}
.notice b{color:var(--ink);font-weight:600}
.bar{position:sticky;top:0;z-index:5;padding-block:14px;border-bottom:1px solid var(--line);
     background:#f5f8fbd9;backdrop-filter:blur(10px)}
.bar .wrap{display:flex;gap:10px 14px;align-items:center;flex-wrap:wrap}
#q{flex:1 1 280px;font:inherit;font-size:var(--t-body);
   padding:11px 18px;border:1.5px solid var(--ink);border-radius:999px;
   background:var(--panel);color:var(--ink)}
#q::placeholder{color:var(--ink-3)}
.chips{display:flex;gap:7px;flex-wrap:wrap}
#view{position:relative;padding-right:14px;margin-right:4px;border-right:1px solid var(--line)}
.chip{font:inherit;font-family:var(--serif);font-size:var(--t-small);font-weight:500;
      padding:.5em 1.1em;border-radius:999px;cursor:pointer;
      border:1px solid var(--line-2);background:transparent;color:var(--ink-2);
      transition:background .18s,border-color .18s,color .18s}
.chip:hover{border-color:var(--ink);color:var(--ink)}
.chip[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff}
.chip b{font-family:var(--mono);font-size:11px;font-weight:400;margin-left:7px;opacity:.65}
.pick{position:relative;display:inline-flex;align-items:center;margin-left:auto}
.pick::after{content:"";position:absolute;right:17px;width:7px;height:7px;pointer-events:none;
             border-right:1.5px solid var(--ink-2);border-bottom:1.5px solid var(--ink-2);
             transform:translateY(-2px) rotate(45deg)}
.pick select{appearance:none;font:inherit;font-family:var(--serif);font-size:var(--t-small);
             font-weight:500;color:var(--ink);background:var(--panel);cursor:pointer;
             border:1px solid var(--line-2);border-radius:999px;padding:.62em 2.8em .62em 1.2em;
             transition:border-color .18s}
.pick select:hover{border-color:var(--ink)}
.pick[hidden]{display:none}

/* `.wrap` carries `margin:0 auto`, and an auto cross-axis margin on a flex
   item stops it stretching: without this the list column is as wide as its
   widest row rather than as wide as the page. */
main.wrap{width:100%}
main{flex:1;padding-bottom:clamp(56px,6vw,96px);min-height:40vh}
.count{font-family:var(--mono);font-size:var(--t-meta);color:var(--ink-3);padding:22px 0 8px}
.row{display:block;width:100%;text-align:left;background:transparent;border:0;
     border-top:1px solid var(--line);padding:15px 2px;cursor:pointer;font:inherit;color:inherit}
.row:hover{background:#fff8}
.row h3{font-family:var(--serif);font-weight:400;font-size:var(--t-row);
        letter-spacing:-.015em;margin:0 0 5px;line-height:1.35}
.meta{font-family:var(--mono);font-size:var(--t-meta);color:var(--ink-3);
      display:flex;gap:11px;flex-wrap:wrap;align-items:baseline}
.tag{font-family:var(--mono);font-size:10px;letter-spacing:.06em;text-transform:uppercase;
     padding:2px 8px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-3);
     white-space:nowrap}
.tag.bg{border-color:var(--line)}
.tag.has{border-color:var(--green);color:var(--green);background:var(--green-bg)}
.none{padding:40px 0;color:var(--ink-2);max-width:62ch;border-top:1px solid var(--line)}
.row.static{cursor:default}
.row.static:hover{background:transparent}
.meta a{color:var(--green);border-bottom:1px solid var(--green-bg)}
.meta a:hover{border-color:var(--green)}
.none a{color:var(--green);border-bottom:1px solid var(--green-bg)}
.why{color:var(--ink-2);font-size:var(--t-small);margin:9px 0 0;max-width:78ch;line-height:1.55}

dialog{border:0;border-radius:var(--radius);padding:0;max-width:780px;width:min(92vw,780px);
       background:var(--panel);color:var(--ink);box-shadow:0 24px 70px #0b1b2a2e}
dialog::backdrop{background:#0b1b2a7a}
.sheet{padding:clamp(24px,3vw,40px)}
.sheet h2{font-family:var(--serif);font-weight:400;font-size:var(--t-heading);
          letter-spacing:-.03em;line-height:1.14;margin:0 0 12px}
.sheet .meta{margin-bottom:18px}
.byline{color:var(--ink-2);font-size:var(--t-small);margin:0 0 14px}
.blurb{color:var(--ink-2);margin:0 0 20px;line-height:1.55}
.sect{border-top:1px solid var(--line);padding-top:18px;margin-top:20px}
.sect h4{font-family:var(--mono);font-size:var(--t-meta);letter-spacing:.09em;
         text-transform:uppercase;color:var(--ink-3);margin:0 0 12px;font-weight:400}
.claim{border-left:2px solid var(--green-bg);padding:0 0 0 14px;margin:0 0 16px}
.claim p{margin:0 0 5px}
.claim q{display:block;color:var(--ink-2);font-size:var(--t-small);margin-top:5px;line-height:1.55}
.claim .meta{margin:7px 0 0}
.links{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}
.ghost{display:inline-flex;align-items:center;gap:8px;font:inherit;font-family:var(--serif);
       font-size:var(--t-small);font-weight:500;padding:.55em 1.1em;border-radius:999px;
       border:1px solid var(--line-2);color:var(--ink-2);background:transparent;cursor:pointer;
       transition:border-color .18s,color .18s}
.ghost:hover{border-color:var(--ink);color:var(--ink)}
.x{position:absolute;top:14px;right:16px;border:0;background:transparent;font-size:24px;
   line-height:1;cursor:pointer;color:var(--ink-3);padding:4px 8px}

/* the dark footer every page of aocommons.org ends with, in its short form */
.site-foot{background:#0b0b0d;color:#f4f4f2;margin-top:auto}
.site-foot .wrap{padding-block:clamp(40px,5vw,72px) calc(28px + env(safe-area-inset-bottom,0px))}
.foot__top{display:grid;grid-template-columns:auto minmax(0,1fr);gap:20px clamp(32px,5vw,80px);
           align-items:start}
.foot__cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,34ch),1fr));
            gap:16px clamp(28px,4vw,64px)}
.site-foot .wordmark{color:#fff}
.site-foot p{margin:0;max-width:58ch;font-size:var(--t-small);line-height:1.6;color:#a3a39e}
.site-foot a{color:#c9c9c4;border-bottom:1px solid #4a4a47}
.site-foot a:hover{color:#fff;border-color:#fff}
.foot__base{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;
            margin-top:clamp(32px,4vw,56px);padding-top:22px;border-top:1px solid #2a2a28}
.site-foot small{font-family:var(--mono);font-size:var(--t-meta);letter-spacing:.04em;color:#8b8b86}

@media (max-width:900px){.top__what,.top__rule{display:none}}
@media (max-width:760px){
  .top .wrap{display:flex;flex-wrap:wrap}
  .top__right{margin-left:auto}
  .foot__top{grid-template-columns:1fr}
}
@media (prefers-reduced-motion:no-preference){.row{transition:background .12s}}
</style>

<header class="top">
  <div class="wrap">
    <span class="top__brand">
      <a href="https://aocommons.org" class="wordmark">AO Commons</a>
      <span class="top__rule" aria-hidden="true">|</span>
      <span class="top__what">Knowledge Graph</span>
      <span class="beta">Preview</span>
    </span>
    <span class="top__right">
      <a class="btn btn--green" id="suggest" href="#">Suggest an addition</a>
      <a class="btn" id="fixAny" href="#">Report an error</a>
    </span>
  </div>
</header>

<section class="intro">
  <div class="wrap">
    <div class="intro__lead">
      <p class="notice notice--lead">We're building an open knowledge graph to help
        advance research on autonomous organizations and multi-agent systems.</p>
      <p class="notice notice--lead">By connecting papers, findings, evidence, and open
        questions, we aim to help researchers build on each other's work, identify
        important gaps, and turn unanswered questions into new research.</p>
      <p class="notice notice--lead">The goal is a shared resource that grows with the
        field, shaped by the researchers contributing to it.</p>
    </div>
    <div class="intro__note">
      <p class="notice"><b>Early preview.</b> The research collection is incomplete, and
        many claims have been extracted by AI without human review. We're gradually
        expanding coverage and functionality with contributions from authors and
        researchers who can help add missing work, correct information, and connect
        related findings.</p>
      <p class="notice">For now, you can suggest individual additions or corrections
        through <a href="https://github.com/AO-Commons/knowledge-graph/issues">GitHub
        issues</a>. We're also testing an improved contribution interface in a private,
        invite-only beta. <b>The easiest way to contribute more actively is to join the
        beta</b> by filling out the
        <a href="https://aocommons.org/#get-involved">interest form</a>.</p>
    </div>
  </div>
</section>

<div class="bar">
  <div class="wrap">
    <div class="chips" id="view" role="group" aria-label="Which records to show"></div>
    <input id="q" type="search" placeholder="Search titles, authors, claims…" autocomplete="off" aria-label="Search">
    <label class="pick" id="kindPick"><select id="kind" aria-label="Kind of record"></select></label>
  </div>
</div>

<main class="wrap">
  <p class="count" id="count"></p>
  <div id="list"></div>
</main>

<footer class="site-foot">
  <div class="wrap">
    <div class="foot__top">
      <a href="https://aocommons.org" class="wordmark">AO Commons</a>
      <div class="foot__cols">
        <p>All data and code are in a
          <a href="https://github.com/AO-Commons/knowledge-graph">public GitHub repository</a>.
          To suggest research, correct a record, or help with the code, see the
          <a href="https://github.com/AO-Commons/knowledge-graph/blob/main/CONTRIBUTING.md">contributing
          guide</a>.</p>
        <p>The corpus is
          <a href="https://github.com/AO-Commons/knowledge-graph/blob/main/LICENSE">CC BY 4.0</a>
          and the code that builds it is
          <a href="https://github.com/AO-Commons/knowledge-graph/blob/main/LICENSE-CODE">MIT</a>:
          use either, and credit the corpus. If you cite it, cite a
          <a href="https://github.com/AO-Commons/knowledge-graph/releases">release</a> rather than
          this page — releases are checksummed and keep their mistakes, so a citation to one
          means the same thing next year.</p>
      </div>
    </div>
    <div class="foot__base">
      <small id="built"></small>
      <small>Knowledge Graph · preview</small>
    </div>
  </div>
</footer>

<dialog id="sheet"><button class="x" aria-label="Close">&times;</button><div class="sheet" id="sheetBody"></div></dialog>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const ISSUES = "__ISSUES__";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Which records the page shows. It opens on the curated set — the records a
// person put on the list in data/curated.yml — because a reader should not
// have to guess which of the graph's records AO Commons stands behind. The
// rest are one button away: nothing is hidden, and nothing is deleted.
let only = true;

// The three a reader almost always wants, in the order they ask for them;
// anything else the corpus holds follows alphabetically. Papers are the
// default because they are what the library is mostly made of — landing on
// everything meant landing on a list whose first screen answered no question.
const KIND_ORDER = ['Paper', 'Deployment', 'Benchmark'];
const DEFAULT_KIND = 'Paper';
let kind = DEFAULT_KIND, q = '';

const CURATED = new Set(D.records.filter(r => r.curated).map(r => r.id));
const shown = () => only ? D.records.filter(r => r.curated) : D.records;

$('#built').textContent = D.release
  ? `${D.release} · built ${D.built}` : `Built ${D.built}`;

$('#view').innerHTML = [['1', 'Curated', D.counts.curated],
                        ['', 'Everything', D.counts.records]]
  .map(([v, label, n]) =>
    `<button class="chip" data-v="${v}" aria-pressed="${!!v === only}">${label}<b>${n}</b></button>`
  ).join('');
$('#view').addEventListener('click', e => {
  const b = e.target.closest('.chip'); if (!b) return;
  only = !!b.dataset.v; kind = DEFAULT_KIND;
  [...$('#view').children].forEach(c => c.setAttribute('aria-pressed', c === b));
  kindlist(); draw();
});

function kindlist() {
  const present = [...new Set(shown().map(r => r.kind))];
  const kinds = [...KIND_ORDER.filter(k => present.includes(k)),
                 ...present.filter(k => !KIND_ORDER.includes(k)).sort()];
  // The curated set and the whole graph do not hold the same kinds, so a
  // selection can stop existing when the view changes. Falling back to the
  // default rather than to nothing keeps the list showing something.
  if (!kinds.includes(kind)) kind = kinds.includes(DEFAULT_KIND) ? DEFAULT_KIND : '';
  $('#kind').innerHTML = [['', 'All kinds'], ...kinds.map(k => [k, k])].map(([v, label]) =>
    `<option value="${esc(v)}"${v === kind ? ' selected' : ''}>${esc(label)}</option>`).join('');
}
$('#kind').addEventListener('change', e => { kind = e.target.value; draw(); });

// Search covers what somebody actually types: a title, a name they half
// remember, an organization, or a phrase from a claim.
const hay = r => (r._hay ??= [
  r.title, r.authors.join(' '), r.orgs.join(' '), r.year, r.id, r.blurb,
  r.claims.map(c => c.text + ' ' + c.quote).join(' '),
].join(' ').toLowerCase());

const matches = r => (!kind || r.kind === kind) &&
  (!q || q.split(/\s+/).every(t => hay(r).includes(t)));

const hits = () => shown().filter(matches);
// Tooltips for the tags, in the words of the definitions in models.py.
const CLAIM_KIND = {
  evidence: 'Something the work reports as observed or measured.',
  position: 'An argument or recommendation, made without evidence in this work.',
  protocol: 'A technique, architecture, or mechanism the work introduces or uses.',
  definition: 'A term the work introduces or defines.',
  gap: 'A question the work says is still open.',
  limitation: 'A limit the authors put on their own result.',
  background: 'A statement about the field or prior work, not this work\'s own contribution.',
};
const ROLE = {
  primitive: 'Where the field\'s vocabulary comes from.',
  anchor: 'A deployment or result the field keeps returning to.',
  benchmark: 'What claims are measured against.',
  method: 'A technique or instrument others use.',
  law: 'Legal and regulatory scholarship bearing on the field.',
  survey: 'Brings a field together rather than adding a result.',
  context: 'Adjacent work the field borrows from.',
};
const RELATED = 'Not about autonomous organizations directly, but relevant to them (for example, economics or law).';
const CURATED_IS = 'On the list behind the AO Commons research agenda, or published on aocommons.org, rather than found by the citation scan.';
const tip = (label, text, cls) => `<span class="tag${cls ? ' ' + cls : ''}"${
  text ? ` title="${esc(text)}"` : ''}>${esc(label)}</span>`;

function draw() {
  const rows = hits();
  const total = shown().length;
  $('#count').textContent = rows.length === total
    ? `${rows.length} records` : `${rows.length} of ${total} records`;
  $('#list').innerHTML = rows.length ? rows.slice(0, 400).map(card).join('') : empty();
  const more = $('#more'); if (more) more.onclick = e => { e.preventDefault(); showAll(); };
  const miss = $('#missing'); if (miss) miss.onclick = e => { e.preventDefault(); suggest(); };
}

// Nothing found. Which of the two reasons it is matters: a search that would
// hit in the full graph is a view problem, and saying "no matches" to that is
// how a reader concludes the library does not have the paper it has.
function empty() {
  const elsewhere = only
    ? D.records.filter(r => !r.curated && matches(r)).length : 0;
  if (elsewhere) return `<p class="none">Nothing in the curated set.
    <b>${elsewhere}</b> record${elsewhere === 1 ? '' : 's'} elsewhere in the graph
    match${elsewhere === 1 ? 'es' : ''} — <a href="#" id="more">show everything</a>.</p>`;
  return `<p class="none">No matches. The collection is incomplete, and it only covers work
    about organizations where AI agents hold real authority. If something you expected
    is missing, <a href="#" id="missing">suggest it</a>.</p>`;
}

function showAll() {
  only = false;
  [...$('#view').children].forEach(c => c.setAttribute('aria-pressed', !c.dataset.v));
  kindlist(); draw();
}

const title = id => (D.records.find(r => r.id === id) || {}).title || id;

function card(r) {
  const who = r.authors.length
    ? r.authors.slice(0, 3).join(', ') + (r.authors.length > 3 ? ' et al.' : '') : '';
  return `<button class="row" data-id="${esc(r.id)}">
    <h3>${esc(r.title)}</h3>
    <div class="meta">
      ${who ? `<span>${esc(who)}</span>` : ''}${r.year ? `<span>${r.year}</span>` : ''}
      <span class="tag">${esc(r.kind)}</span>
      ${r.claims.length ? `<span class="tag has">${r.claims.length} claims</span>` : ''}
      ${r.background ? `<span class="tag bg" title="${esc(RELATED)}">related field</span>` : ''}
      ${r.role ? tip(r.role, ROLE[r.role]) : ''}
      ${!only && r.curated ? tip('curated', CURATED_IS, 'has') : ''}
    </div></button>`;
}

$('#list').addEventListener('click', e => {
  const go = e.target.closest('[data-go]');
  if (go) { e.preventDefault(); openRecord(go.dataset.go); return; }
  const row = e.target.closest('.row[data-id]');
  if (row) openRecord(row.dataset.id);
});

// Not `open`: a top-level `function open` IS `window.open`, so every
// issue link called this with a URL and failed silently.
function openRecord(id) {
  const r = D.records.find(x => x.id === id); if (!r) return;
  const topics = r.topics.map(t => D.topics[t] ? `${t} ${D.topics[t]}` : t);
  const also = r.authors.flatMap(a => (D.people[a] || []).filter(x => x !== id)
    .map(x => ({ a, x }))).slice(0, 6);
  const asks = r.asks.map(qid => (D.asked[qid] || {}).text).filter(Boolean);

  $('#sheetBody').innerHTML = `
    <h2>${esc(r.title)}</h2>
    <div class="meta">
      ${r.year ? `<span>${r.year}</span>` : ''}<span class="tag">${esc(r.kind)}</span>
      ${r.background ? `<span class="tag bg" title="${esc(RELATED)}">related field</span>` : ''}
      ${r.role ? tip(r.role, ROLE[r.role]) : ''}
      ${r.curated ? tip('curated', CURATED_IS, 'has') : ''}
      <span>${esc(r.id)}</span>
    </div>
    ${r.authors.length ? `<p class="byline">${esc(r.authors.join(', '))}</p>` : ''}
    ${r.orgs.length ? `<p class="byline">${esc(r.orgs.join(' · '))}</p>` : ''}
    ${r.blurb ? `<p class="blurb">${esc(r.blurb)}</p>` : ''}

    ${topics.length ? sect('Topics', topics.map(t =>
      `<span class="tag">${esc(t)}</span>`).join(' ')) : ''}

    ${r.claims.length ? sect(`Claims (${r.claims.length})`,
      `<p class="blurb">Drafted by a model, each with the sentence it was taken from.
        Only claims marked "checked by a person" have been compared with the source.</p>` +
      r.claims.map(c => `<div class="claim">
        <p>${esc(c.text)}</p>
        <q>${esc(c.quote)}</q>
        <div class="meta">${tip(c.kind, CLAIM_KIND[c.kind])}
          ${c.own ? '' : `<span class="tag">cites ${esc(c.whose || 'another author')}</span>`}
          ${c.reviewed ? '<span class="tag has">checked by a person</span>' : ''}</div>
      </div>`).join('')) : sect('Claims',
        `<p class="blurb">No claims yet. ${r.coverage === 'none'
          ? 'We don\'t have the full text, so claims can\'t be drafted from it.'
          : 'Claims haven\'t been drafted from this record yet.'}</p>`)}

    ${asks.length ? sect('Open questions it raises',
      asks.map(t => `<p class="blurb">${esc(t)}</p>`).join('')) : ''}

    ${also.length ? sect('Also by these authors', also.map(({ a, x }) => {
      const o = D.records.find(z => z.id === x);
      return o ? `<p class="blurb"><a href="#" data-go="${esc(o.id)}">${esc(o.title)}</a>
        <span class="meta"> · ${esc(a)}</span></p>` : '';
    }).join('')) : ''}

    <div class="links">
      ${r.url ? `<a class="ghost" href="${esc(r.url)}" target="_blank" rel="noopener">Open the source ↗</a>` : ''}
      ${readable(r) ? `<a class="ghost" id="read" href="#">Request claim extraction</a>` : ''}
      <a class="ghost" id="fix" href="#">Report an error</a>
    </div>`;

  $('#fix').onclick = e => { e.preventDefault(); correct(r); };
  const ask = $('#read'); if (ask) ask.onclick = e => { e.preventDefault(); request(r); };
  $('#sheetBody').querySelectorAll('[data-go]').forEach(a =>
    a.onclick = e => { e.preventDefault(); openRecord(a.dataset.go); });
  $('#sheet').showModal();
}

const sect = (h, body) => `<div class="sect"><h4>${esc(h)}</h4>${body}</div>`;

function issue(template, fields, title) {
  const p = new URLSearchParams({ template, title });
  for (const [k, v] of Object.entries(fields)) if (v) p.set(k, v);
  window.open(`${ISSUES}?${p}`, '_blank', 'noopener');
}
const correct = r => issue('request-adjustment.yml',
  { record: r.id }, `[Fix] ${r.title}`.slice(0, 120));
// Reading is a model call over a whole paper, so the door is narrow on
// purpose: a curated paper, with an arXiv id, that nobody has read yet.
// The same three things `scripts/read_paper.py` checks — asking for a
// reading it is going to refuse teaches people the button does not work.
const readable = r => r.curated && !r.claims.length && /^resource:arxiv:/.test(r.id);
const request = r => issue('read-paper.yml',
  { record: r.id }, `[Read] ${r.title}`.slice(0, 120));
const suggest = () => issue('suggest-addition.yml', {}, '[Add] ');

$('#suggest').onclick = e => { e.preventDefault(); suggest(); };
$('#fixAny').onclick = e => { e.preventDefault(); issue('request-adjustment.yml', {}, '[Fix] '); };
$('#sheet').querySelector('.x').onclick = () => $('#sheet').close();

$('#q').addEventListener('input', e => { q = e.target.value.trim().toLowerCase(); draw(); });
kindlist();
addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== $('#q')) { e.preventDefault(); $('#q').focus(); }
});
draw();
</script>
"""

if __name__ == "__main__":
    sys.exit(main())
