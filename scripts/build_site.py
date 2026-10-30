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
render when a sibling repository moves a file.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

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
    "platform": "Deployment", "deployment": "Deployment",
    "evaluation-suite": "Benchmark", "benchmark": "Benchmark",
    "research-programme": "Programme", "standard": "Standard",
}


def payload() -> dict:
    resources = load_resources()
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

    return {
        "built": __import__("datetime").date.today().isoformat(),
        "records": sorted(records, key=lambda r: (bool(r["claims"]), r["year"] or "0000"),
                          reverse=True),
        "topics": topics,
        "questions": {q.id: q.text for q in questions},
        "people": {p["name"]: p["records"] for p in people_index(resources)},
        "counts": {
            "records": len(resources),
            "claims": len(claims),
            "read": len(by_resource),
            "reviewed": sum(1 for c in claims if c.verdict),
            "questions": len(questions),
            "topics": len(topics),
        },
    }


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
<title>Knowledge Graph — AO Commons</title>
<meta name="description" content="A maintained map of research on autonomous organizations: organizations in which machine agents hold operational or decision authority.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,500&family=Hanken+Grotesk:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap">
<style>
/* AO Commons tokens, copied from the website's src/shared/tokens.css. */
:root{
  --bg:#f5f8fb; --sky:#cfe4f7; --panel:#fff; --panel-2:#ebebe8;
  --ink:#1a1a19; --ink-2:#5a5a57; --ink-3:#8b8b86;
  --line:#d9d9d5; --line-2:#bdbdb8;
  --green:#0e4f46; --green-ink:#0a3c35; --green-bg:#dde9e6;
  --serif:"Bricolage Grotesque","Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --sans:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --mono:"DM Mono","SFMono-Regular",Menlo,monospace;
  --gutter:clamp(20px,4vw,64px);
  --max:1180px;
  --inset:max(var(--gutter), calc((100vw - var(--max)) / 2 + var(--gutter)));
  color-scheme:light;
}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,var(--sky) 0,var(--bg) 46vh) no-repeat,var(--bg);
     color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.5;
     -webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{padding-inline:var(--inset);max-width:calc(var(--max) + 2*var(--gutter));margin:0 auto}

header{padding-block:clamp(26px,4vw,52px) 10px}
.brand{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.brand b{font-family:var(--serif);font-weight:400;font-size:clamp(22px,2.2vw,30px);letter-spacing:-.02em}
.brand span{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}
h1{font-family:var(--serif);font-weight:300;letter-spacing:-.035em;line-height:1.04;
   font-size:clamp(34px,4.6vw,62px);margin:.42em 0 .3em;max-width:20ch}
.lede{font-size:clamp(17px,1.4vw,20px);color:var(--ink-2);max-width:60ch;margin:0}
.figs{display:flex;gap:clamp(16px,2.4vw,38px);flex-wrap:wrap;margin:26px 0 0;
      font-family:var(--mono);font-size:12.5px;color:var(--ink-2)}
.figs b{font-family:var(--sans);font-size:19px;font-weight:600;color:var(--ink);margin-right:6px}

.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
     margin-top:30px;padding-block:13px}
.bar .wrap{display:flex;gap:10px 12px;align-items:center;flex-wrap:wrap}
.bar .wrap{--pad:0}#q{flex:1 1 260px}.chips{flex:1 1 auto}
#q{flex:1;min-width:240px;font:inherit;font-size:16.5px;padding:11px 15px;border-radius:10px;
   border:1px solid var(--line-2);background:var(--panel);color:var(--ink)}
#q:focus{outline:2px solid var(--green);outline-offset:1px;border-color:transparent}
.chips{display:flex;gap:7px;flex-wrap:wrap}
.chip{font:inherit;font-size:13px;padding:7px 13px;border-radius:999px;cursor:pointer;
      border:1px solid var(--line-2);background:transparent;color:var(--ink-2)}
.chip[aria-pressed=true]{background:var(--green);border-color:var(--green);color:#fff}
.add{font:inherit;font-family:var(--serif);font-size:15px;padding:10px 18px;border-radius:999px;
     background:var(--green);color:#fff;border:0;cursor:pointer;text-decoration:none;white-space:nowrap}
.add:hover{background:var(--green-ink)}

main{padding-bottom:90px}
.count{font-family:var(--mono);font-size:12px;color:var(--ink-3);padding:18px 0 8px}
.row{display:block;width:100%;text-align:left;background:transparent;border:0;border-bottom:1px solid var(--line);
     padding:17px 2px;cursor:pointer;font:inherit;color:inherit}
.row:hover{background:#fff8}
.row h3{font-family:var(--serif);font-weight:400;font-size:clamp(17px,1.25vw,20px);
        letter-spacing:-.015em;margin:0 0 5px;line-height:1.26}
.meta{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);display:flex;gap:11px;flex-wrap:wrap}
.tag{border:1px solid var(--line-2);border-radius:999px;padding:1px 9px;white-space:nowrap}
.tag.bg{border-color:var(--line);color:var(--ink-3)}
.tag.has{border-color:var(--green);color:var(--green)}
.none{padding:40px 0;color:var(--ink-2)}

dialog{border:0;border-radius:16px;padding:0;max-width:760px;width:min(92vw,760px);
       background:var(--panel);color:var(--ink);box-shadow:0 24px 70px #0b1b2a2e}
dialog::backdrop{background:#0b1b2a7a}
.sheet{padding:clamp(22px,3vw,36px)}
.sheet h2{font-family:var(--serif);font-weight:400;font-size:clamp(21px,2vw,28px);
          letter-spacing:-.02em;line-height:1.2;margin:0 0 10px}
.sheet .meta{margin-bottom:18px}
.byline{color:var(--ink-2);font-size:15px;margin:0 0 14px}
.blurb{color:var(--ink-2);margin:0 0 20px}
.sect{border-top:1px solid var(--line);padding-top:16px;margin-top:18px}
.sect h4{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;
         color:var(--ink-3);margin:0 0 11px;font-weight:400}
.claim{border-left:2px solid var(--green-bg);padding:0 0 0 14px;margin:0 0 15px}
.claim p{margin:0 0 5px}
.claim q{display:block;color:var(--ink-2);font-size:14.5px;margin-top:5px}
.claim .meta{margin:6px 0 0}
.links{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.ghost{font:inherit;font-size:14px;padding:9px 16px;border-radius:999px;text-decoration:none;
       border:1px solid var(--line-2);color:var(--ink);background:transparent;cursor:pointer}
.ghost:hover{border-color:var(--ink-3)}
.x{position:absolute;top:14px;right:16px;border:0;background:transparent;font-size:24px;
   line-height:1;cursor:pointer;color:var(--ink-3);padding:4px 8px}
footer{border-top:1px solid var(--line);padding:26px 0 60px;font-size:14px;color:var(--ink-2)}
footer a{color:var(--green)}
@media (prefers-reduced-motion:no-preference){.row{transition:background .12s}}
</style>

<header>
  <div class="wrap">
    <div class="brand"><b>AO Commons</b><span>Knowledge Graph</span></div>
    <h1>Research on organizations machines help run.</h1>
    <p class="lede">A maintained map of work on <b>autonomous organizations</b>: organizations in
      which machine agents hold operational or decision authority. Every claim here carries the
      sentence it was drawn from, so you can check it without opening the paper.</p>
    <div class="figs" id="figs"></div>
  </div>
</header>

<div class="bar">
  <div class="wrap">
    <input id="q" type="search" placeholder="Search titles, authors, organizations, claims…"
           autocomplete="off" aria-label="Search the library">
    <div class="chips" id="chips"></div>
    <a class="add" id="suggest" href="#">Suggest something</a>
  </div>
</div>

<main class="wrap">
  <p class="count" id="count"></p>
  <div id="list"></div>
</main>

<footer class="wrap">
  <p>An early preview. Everything is a file in a
    <a href="https://github.com/AO-Commons/knowledge-graph">public git repository</a> — readable,
    diffable and citable at a fixed version. Corrections are the most useful thing you can send.</p>
  <p id="built"></p>
</footer>

<dialog id="sheet"><button class="x" aria-label="Close">&times;</button><div class="sheet" id="sheetBody"></div></dialog>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const ISSUES = "__ISSUES__";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

$('#figs').innerHTML = [
  [D.counts.records,'records'], [D.counts.claims,'claims'],
  [D.counts.read,'papers read'], [D.counts.reviewed,'checked by a person'],
  [D.counts.questions,'open questions'],
].map(([n,l]) => `<span><b>${n}</b>${l}</span>`).join('');
$('#built').textContent = `Built ${D.built}.`;

const KINDS = [...new Set(D.records.map(r => r.kind))].sort();
let kind = '', q = '';
$('#chips').innerHTML = ['All', ...KINDS].map(k =>
  `<button class="chip" data-k="${k === 'All' ? '' : esc(k)}" aria-pressed="${k === 'All'}">${esc(k)}</button>`
).join('');
$('#chips').addEventListener('click', e => {
  const b = e.target.closest('.chip'); if (!b) return;
  kind = b.dataset.k;
  [...$('#chips').children].forEach(c => c.setAttribute('aria-pressed', c === b));
  draw();
});

// Search covers what somebody actually types: a title, a name they half
// remember, an organization, or a phrase from a claim.
const hay = r => (r._hay ??= [
  r.title, r.authors.join(' '), r.orgs.join(' '), r.year, r.id, r.blurb,
  r.claims.map(c => c.text + ' ' + c.quote).join(' '),
].join(' ').toLowerCase());

function matches(r) {
  if (kind && r.kind !== kind) return false;
  if (!q) return true;
  return q.split(/\s+/).every(t => hay(r).includes(t));
}

function draw() {
  const hits = D.records.filter(matches);
  $('#count').textContent = hits.length === D.records.length
    ? `${hits.length} records`
    : `${hits.length} of ${D.records.length} records`;
  $('#list').innerHTML = hits.length ? hits.slice(0, 400).map(card).join('')
    : `<p class="none">Nothing matches that. The library is deliberately narrow — if something
       you expected is missing, <a href="#" id="missing">tell us</a>.</p>`;
  if (!hits.length) $('#missing').onclick = e => { e.preventDefault(); suggest(); };
}

function card(r) {
  const who = r.authors.length
    ? r.authors.slice(0, 3).join(', ') + (r.authors.length > 3 ? ' et al.' : '') : '';
  return `<button class="row" data-id="${esc(r.id)}">
    <h3>${esc(r.title)}</h3>
    <div class="meta">
      ${who ? `<span>${esc(who)}</span>` : ''}${r.year ? `<span>${r.year}</span>` : ''}
      <span class="tag">${esc(r.kind)}</span>
      ${r.claims.length ? `<span class="tag has">${r.claims.length} claims</span>` : ''}
      ${r.background ? `<span class="tag bg">background</span>` : ''}
      ${r.role ? `<span class="tag">${esc(r.role)}</span>` : ''}
    </div></button>`;
}

$('#list').addEventListener('click', e => {
  const row = e.target.closest('.row'); if (row) open(row.dataset.id);
});

function open(id) {
  const r = D.records.find(x => x.id === id); if (!r) return;
  const topics = r.topics.map(t => D.topics[t] ? `${t} ${D.topics[t]}` : t);
  const also = r.authors.flatMap(a => (D.people[a] || []).filter(x => x !== id)
    .map(x => ({ a, x }))).slice(0, 6);
  const asks = r.asks.map(qid => D.questions[qid]).filter(Boolean);

  $('#sheetBody').innerHTML = `
    <h2>${esc(r.title)}</h2>
    <div class="meta">
      ${r.year ? `<span>${r.year}</span>` : ''}<span class="tag">${esc(r.kind)}</span>
      ${r.background ? `<span class="tag bg">section 15 background</span>` : ''}
      ${r.role ? `<span class="tag">${esc(r.role)}</span>` : ''}
      <span>${esc(r.id)}</span>
    </div>
    ${r.authors.length ? `<p class="byline">${esc(r.authors.join(', '))}</p>` : ''}
    ${r.orgs.length ? `<p class="byline">${esc(r.orgs.join(' · '))}</p>` : ''}
    ${r.blurb ? `<p class="blurb">${esc(r.blurb)}</p>` : ''}

    ${topics.length ? sect('Filed under', topics.map(t =>
      `<span class="tag">${esc(t)}</span>`).join(' ')) : ''}

    ${r.claims.length ? sect(`What it says — ${r.claims.length} claims, each with its source sentence`,
      r.claims.map(c => `<div class="claim">
        <p>${esc(c.text)}</p>
        <q>${esc(c.quote)}</q>
        <div class="meta"><span class="tag">${esc(c.kind)}</span>
          ${c.own ? '' : `<span class="tag">reports ${esc(c.whose || 'another author')}</span>`}
          ${c.reviewed ? '<span class="tag has">checked by a person</span>' : ''}</div>
      </div>`).join('')) : sect('What it says',
        `<p class="blurb">Held, not yet read. ${r.coverage === 'none'
          ? 'There is no full text to read it from — it is pointed at rather than ingested.'
          : 'Nobody has drawn claims out of it.'}</p>`)}

    ${asks.length ? sect('Open questions it bears on',
      asks.map(t => `<p class="blurb">${esc(t)}</p>`).join('')) : ''}

    ${also.length ? sect('Also by these authors', also.map(({ a, x }) => {
      const o = D.records.find(z => z.id === x);
      return o ? `<p class="blurb"><a href="#" data-go="${esc(o.id)}">${esc(o.title)}</a>
        <span class="meta"> — ${esc(a)}</span></p>` : '';
    }).join('')) : ''}

    <div class="links">
      ${r.url ? `<a class="ghost" href="${esc(r.url)}" target="_blank" rel="noopener">Open the source ↗</a>` : ''}
      <a class="ghost" id="fix" href="#">Something here is wrong</a>
    </div>`;

  $('#fix').onclick = e => { e.preventDefault(); correct(r); };
  $('#sheetBody').querySelectorAll('[data-go]').forEach(a =>
    a.onclick = e => { e.preventDefault(); open(a.dataset.go); });
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
const suggest = () => issue('suggest-addition.yml', {}, '[Add] ');

$('#suggest').onclick = e => { e.preventDefault(); suggest(); };
$('#sheet').querySelector('.x').onclick = () => $('#sheet').close();

$('#q').addEventListener('input', e => { q = e.target.value.trim().toLowerCase(); draw(); });
addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== $('#q')) { e.preventDefault(); $('#q').focus(); }
});
draw();
</script>
"""

if __name__ == "__main__":
    sys.exit(main())
