---
id: types
title: Statement kinds
kicker: seven, and why tagging differs by kind
order: 6
---

Findings and positions are what somebody came for: what has been shown, and
what has been argued. The rest give a reader what they need to judge those.
The review screen groups them that way for the same reason.

| Kind | Held | Is | How it is tagged |
| --- | --- | --- | --- |
| finding | {{kind.finding}} | Something the work reports as observed or measured. | With its subject — what the result is about. |
| position | {{kind.position}} | An argument or recommendation, offered without evidence here. "Agents with budget caps overspent less" and "agents should have budget caps" look alike in an abstract and answer different questions. | With its subject, like a finding. |
| method | {{kind.method}} | A technique or mechanism the work introduces or uses — how something is done. | With the technique, never the paper's subject. That is what makes "who found this, working that way" answerable; a method carrying only its paper's subject is flagged at extraction. |
| definition | {{kind.definition}} | A term the work introduces or fixes the meaning of. Before this type, definitions were filed as methods, and a paper that defined a technique answered "who found this, working that way" as though it had used it. | With the concept it defines, so "who coined this, and how did they define it" is the definitions carrying that tag. |
| background | {{kind.background}} | An assertion about the field or prior work rather than this paper's own contribution. Usually somebody else's result, asserted without evidence, and it dates badly. | Attribution matters more than the tag: whose result is it. Asked at extraction, because finding it later means rereading. |
| gap | {{kind.gap}} | A question the paper says is open — one it leaves open itself, or one it reports the field has not answered. Where a limitation bounds this result, a gap says what nobody has answered yet. | With the subject of the question. These are what questions are clustered from, so the tag is what joins one paper's open question to another's. |
| limitation | {{kind.limitation}} | What the work says it cannot do or did not test. | Rare and worth hunting — they live in discussion sections, and they are the part a downstream reader most often drops. |

Of {{statements}} statements held, {{primary}} are primary. A paper's yield is
its primary count, not its statement count.
