---
id: pipeline
title: From a paper to a statement
kicker: nine stages
order: 6
---

What happens between a paper arriving and its statements being citable, who or
what does each part, and how far it actually goes today. The scaffolding is
complete and thins sharply toward the top.

| Stage | Who | What happens | Where it stands |
| --- | --- | --- | --- |
| 1 Intake | machine | Three doors, one destination: the Add tab for one paper, a bulk script for a reading list, and the weekly crawl of the citation graph. Each record says which door it came through. | {{records}} records |
| 2 Resolution | machine | OpenAlex for identity, citations and institutions; Semantic Scholar for preprint abstracts and references; arXiv last and decisive for the byline, because the submission beats an index's guess. | citations inside the corpus |
| 3 Admission | machine | Two routes in, and the difference between them is what evidence a candidate arrives with. Both end at the same scope scan. | runs Tuesdays |
| 3a Growth | machine | `aokg grow` walks the citation graph both ways. Backward is free; forward costs a query per held record and is the only route by which recent research can arrive at all — a paper published last month has been cited by nobody, but it can cite three of ours on the day it appears. | 40 a run |
| 3b Scouting | machine | `scripts/scout.py` looks for work the citation graph cannot see. It proposes and never admits: a search result has no vote, so it writes a candidate file and a person decides. | dispatch only |
| 4 Extraction | machine, then a person | Statements read out of the full text, each with a verbatim quote, through five gates. Reaching the text at all is the real ceiling: only arXiv has a path. | {{read}} of {{records}} papers |
| 5 Tagging | machine, then a person | Concepts on statements, fine-grained on purpose. The vocabulary grows from the bottom up — a term is in it because a statement argued about something. | concepts in use |
| 6 Linking | a person | Shared concepts propose pairs; people assert the relation and write down why. Most candidates should be nothing — a high yield would mean the vocabulary is too loose. | relations asserted |
| 7 Filing | machine | A paper's categories are the union of the topics its statements' concepts sit under. Computed, no judgment. | computed |
| 8 Review | a person | The scarce good, and the one thing no machine does: is each statement what its quote says. A verdict binds to the wording it was given. | {{reviewed}} of {{statements}} |
| 9 Release | machine | A fixed, citable version. Same inputs, same bytes. A release keeps its mistakes; rewriting one would make every other release less trustworthy. | checksummed |

**Where the effort goes.** Intake, resolution, admission, filing and release
run unattended. Extraction, tagging and linking are machine-produced and
marked unconfirmed until somebody says otherwise. Review is irreducible. The
bottom line grows only when somebody reads something, which is why the binding
constraint has moved from "how do we find papers" to "who decides whether any
of this is right".
