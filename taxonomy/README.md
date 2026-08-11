# taxonomy/

| File | Purpose |
|---|---|
| [agentic-org-research-library-taxonomy-v3.md](agentic-org-research-library-taxonomy-v3.md) | **The source of truth.** Everything else is derived from it |
| [aliases.yaml](aliases.yaml) | Synonyms that make a topic findable under other names |
| [crosslinks.yaml](crosslinks.yaml) | Non-hierarchical relationships between topics |
| [proposals/](proposals/) | Proposed additions, one file each |

## What the parser takes from the file

567 topics across the 16 numbered sections. Everything after them — *Facet axes*, *Exclusion register*, *Notes on use* — is reference material, not taxonomy, and the codes quoted inside those sections are cross-references rather than definitions.

**The code is the hierarchy.** `2.2.1` is a child of `2.2` because of its code, not because of how the file indents it. That means reformatting the markdown cannot silently restructure the graph, and a mis-indented line is a cosmetic problem rather than a data one.

**Unnumbered sub-bullets are kept.** 45 lines in the file sit under a numbered topic without a code of their own — "Moral hazard without self-interest" under `1.2.1`, for instance. They are often the most specific phrasing in the taxonomy and exactly what a topic search should match on, so they ride along on the parent as `subpoints`. Giving them codes would violate the rule that codes are stable identifiers.

## Three structures, three implementations

**The numbered hierarchy** is navigation. Tagging a leaf implies relevance to its ancestors, so browsing works without tagging every level.

**Section 11** is a coding scheme. Its 119 topics are marked `usage_mode: coding_scheme` and most incidents carry several at once. Its value is at design time — reading the failure list before deploying, not after.

**F1–F12** are facets, implemented as flat controlled vocabularies on resources rather than as another tree. The taxonomy answers *what is this about*; the facets answer *what kind of evidence is this, and when does it apply*.

## Section shape

Sections 2, 4, 6, 10, and 11 carry the weight; 15 and 16 are shallow on purpose.

Two things the file says about itself, worth preserving as product behaviour:

- **Section 6 is the thinnest literature and the highest leverage.** Treating agents as organizational members — selection, performance management, retirement — has almost no published research, but the operational questions arrive immediately. A large branch with few resources is a research gap worth surfacing, not a defect to paper over. Note that thin *literature* is not a small branch: section 6 has 31 topics.
- **Section 12.1 is mostly empty, and that is the honest state of the field.** Everything in sections 2–10 presupposes someone accountable. Do not fill it with material that doesn't exist.
