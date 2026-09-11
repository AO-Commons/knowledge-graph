"""One spelling, for the text this project writes itself.

The corpus is written by a model, in many sittings, and a model will spell
`organisational` in one statement and `organizational` in the next without
either being wrong. That is fine in prose and not fine here, because a
statement's tags are slugs: `organisational-knowledge-legibility` and
`organizational-knowledge-legibility` are two concepts, joined to nothing,
and two statements about the same idea stop being linkable. American
throughout, because it has to be one or the other.

Not applied to anything a publisher or an author wrote. A `quote` is checked
verbatim against the paper and a resource's title and abstract are what the
paper is called and says — rewriting either would make the corpus disagree
with the thing it points at, and the corpus would be the one that was wrong.
So a statement reading `Artificial Organizational Intelligence` above a quote
reading `Organisational` is correct, and deliberate.
"""

import re

# Grounded in what is actually in the repo rather than in the general case.
# `metre` and `programme` are deliberately absent: `parameter` contains one and
# a `programme` in a British institution's name is that institution's name.
PAIRS = [
    (r"organis", "organiz"), (r"Organis", "Organiz"),
    (r"recognis", "recogniz"), (r"formalis", "formaliz"),
    (r"optimis", "optimiz"), (r"utilis", "utiliz"),
    (r"generalis", "generaliz"), (r"specialis", "specializ"),
    (r"summaris", "summariz"), (r"categoris", "categoriz"),
    (r"characteris", "characteriz"), (r"prioritis", "prioritiz"),
    (r"minimis", "minimiz"), (r"maximis", "maximiz"),
    (r"normalis", "normaliz"), (r"operationalis", "operationaliz"),
    (r"institutionalis", "institutionaliz"), (r"legitimis", "legitimiz"),
    (r"standardis", "standardiz"), (r"decentralis", "decentraliz"),
    (r"centralis", "centraliz"), (r"incentivis", "incentiviz"),
    (r"contextualis", "contextualiz"), (r"conceptualis", "conceptualiz"),
    (r"rationalis", "rationaliz"), (r"marginalis", "marginaliz"),
    (r"internalis", "internaliz"), (r"externalis", "externaliz"),
    (r"stabilis", "stabiliz"), (r"mobilis", "mobiliz"),
    (r"behaviour", "behavior"), (r"Behaviour", "Behavior"),
    (r"colour", "color"), (r"favour", "favor"), (r"labour", "labor"),
    (r"honour", "honor"), (r"rigour", "rigor"), (r"endeavour", "endeavor"),
    (r"modelling", "modeling"), (r"modelled", "modeled"),
    (r"labelling", "labeling"), (r"labelled", "labeled"),
    (r"signalling", "signaling"), (r"signalled", "signaled"),
    (r"travelling", "traveling"), (r"counselling", "counseling"),
    (r"cancelled", "canceled"), (r"fuelled", "fueled"),
    (r"judgement", "judgment"), (r"Judgement", "Judgment"),
    (r"artefact", "artifact"), (r"Artefact", "Artifact"),
    (r"defence", "defense"), (r"offence", "offense"),
    (r"licence", "license"), (r"practise", "practice"),
    (r"fulfil\b", "fulfill"), (r"fulfils", "fulfills"),
    (r"enrol\b", "enroll"), (r"instil\b", "instill"),
    (r"skilful", "skillful"), (r"wilful", "willful"),
    (r"whilst", "while"), (r"amongst", "among"), (r"learnt", "learned"),
    (r"catalogue", "catalog"), (r"Catalogue", "Catalog"),
    (r"centre\b", "center"), (r"Centre\b", "Center"), (r"centres\b", "centers"),
    (r"grey\b", "gray"),
    # `analysis` is spelled the same in both, so only the verb forms move.
    (r"analyse\b", "analyze"), (r"analysed", "analyzed"),
    (r"analyses\b", "analyzes"), (r"analysing", "analyzing"),
]

PATTERN = re.compile("|".join(f"({p})" for p, _ in PAIRS))
_REPL = {p: r for p, r in PAIRS}


def to_american(text: str) -> str:
    def swap(match: re.Match) -> str:
        for (pattern, replacement) in PAIRS:
            if re.fullmatch(pattern, match.group(0)):
                return replacement
        # `\b` and `s` suffixes mean the matched text can be longer than the
        # pattern's literal; fall back to the group that fired.
        for i, (pattern, replacement) in enumerate(PAIRS, start=1):
            if match.group(i) is not None:
                return re.sub(pattern, replacement, match.group(0))
        return match.group(0)
    return PATTERN.sub(swap, text)


def findings(text: str) -> list[str]:
    return [m.group(0) for m in PATTERN.finditer(text or "")]
