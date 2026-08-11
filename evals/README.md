# evals/

The graph has to earn its existence. Before the architecture grows, it should beat the obvious alternatives on real research questions.

```
questions/   20–30 representative AO research questions
gold/        the sources a good answer should surface
results/     runs, per baseline
```

## Baselines

| | Setup |
|---|---|
| **A** | Frontier model, ordinary web research |
| **B** | Frontier model, OpenAlex/Asta directly |
| **C** | Frontier model, a curated folder of metadata with search |
| **AO Commons** | Frontier model querying this graph over MCP |

Baseline C matters most. It is the honest question: does the graph beat a well-organized folder? If it doesn't, the graph is ceremony.

## What to measure

Retrieval quality — were the key papers found, how many irrelevant ones came back, how much of the relevant taxonomy was covered. Cost — tokens, external API calls, how much source text had to be read, time to a useful source set. Answer quality — correctness, citation accuracy, and which output a researcher actually prefers.

Do not optimize graph metrics that don't move these. A denser graph that answers no question better is worse than a sparse one, because it costs more to maintain and more to query.

## Questions

Spread across authority architecture, oversight, multi-agent coordination, memory, security, failure modes, legal accountability, and evaluation — roughly the sections that carry the taxonomy's weight. Each question records the taxonomy codes a good answer should touch, so coverage is measurable rather than impressionistic.

Worth including deliberately: at least one question where **the honest answer is that the literature is thin**. Section 6 and Section 12.1 are nearly empty, and a system that confabulates coverage there is failing in the way that matters most for a research tool.
