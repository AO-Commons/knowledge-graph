"""The same work under a different identifier.

Canonical keys cannot see it. A preprint and its published version have
different DOIs by construction, and OpenAlex indexes them as separate works
— Generative Agents is `W4363671832` as the arXiv preprint and `W4387835442`
as published, so a corpus holding one does not look like it holds the other.

This lived in `scripts/add_resource.py` and guarded only the issue-filing
path, which is the path where a person is watching. The citation expansion,
which runs unattended every week, had no such guard: it re-proposed works
already in the corpus, paid for a scope call on each, and refused them. One
candidate had been judged eight times. Moved here so both paths ask the same
question.
"""
from __future__ import annotations

import difflib
import re

def likely_same_work(payload: dict, resources: list) -> list[tuple[object, str]]:
    """Records that look like the same paper under a different identifier.

    `already_held` compares canonical keys, and a preprint and its published
    version have different DOIs by construction — so it cannot see the case
    that actually happens. Both duplicates found in the first outside
    contribution were this shape:

        EPIC 10.1111/epic.70009   vs  SSRN 10.2139/ssrn.5516298
        Nature 10.1038/s41586-…   vs  arXiv 2504.21848

    The second defeats a title check too: "Characterizing AI Agents for
    Alignment and Governance" was published as "Agentic profiles for
    effective AI governance". What survives retitling is the byline.

    So: the same author set, or a title that barely changed. Reported for a
    person to confirm rather than refused — two papers by the same pair in
    the same year is normal, and blocking on it would make the common case
    pay for the rare one. A sweep over the whole corpus on this signal found
    exactly the one real pair and no false admissions.
    """
    import difflib

    from ao_commons_kg.people import fold

    incoming = {fold(a) for a in payload.get("authors") or []}
    title = re.sub(r"[^a-z0-9 ]", "", (payload.get("title") or "").lower()).strip()
    hits: list[tuple[object, str]] = []

    for resource in resources:
        if resource.id == payload.get("id"):
            continue
        held_authors = {fold(a) for a in (resource.authors or [])}
        held_title = re.sub(r"[^a-z0-9 ]", "", (resource.title or "").lower()).strip()

        if title and held_title:
            ratio = difflib.SequenceMatcher(None, title, held_title).ratio()
            if ratio > 0.9:
                hits.append((resource, f"near-identical title ({ratio:.0%})"))
                continue

        if incoming and held_authors:
            shared = incoming & held_authors
            overlap = len(shared) / len(incoming | held_authors)
            # Two or more shared names and near-identical author sets. One
            # shared name is a co-author, not a duplicate.
            #
            # And the pair must straddle preprint and published. That is what
            # the preprint/version-of-record shape *is*, and it is what
            # separates it from the far more common case of one research
            # group publishing several papers together — which flagged five
            # of eighty-seven records before this condition, every one of
            # them a false positive. Companion preprints posted the same day
            # share a byline and a type; a preprint and its published
            # version share a byline and differ in type.
            straddles = _is_preprint(payload.get("resource_type")) != _is_preprint(
                resource.resource_type)
            if overlap >= 0.8 and len(shared) >= 2 and straddles:
                hits.append((resource, f"same byline across preprint and published "
                                       f"({len(shared)} authors, {overlap:.0%} overlap)"))
    return hits


def _is_preprint(resource_type) -> bool:
    value = getattr(resource_type, "value", resource_type)
    return str(value or "") == "preprint"
