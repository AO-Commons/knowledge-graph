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
    # The -ise family, each with a suffix guard. Without one
    # `characteris` matches inside `characteristic` and yields
    # `characteriztic`, which is how this converter first ran.
    (r"organis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "organiz"),
    (r"Organis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Organiz"),
    (r"recognis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "recogniz"),
    (r"Recognis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Recogniz"),
    (r"formalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "formaliz"),
    (r"Formalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Formaliz"),
    (r"optimis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "optimiz"),
    (r"Optimis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Optimiz"),
    (r"utilis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "utiliz"),
    (r"Utilis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Utiliz"),
    (r"generalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "generaliz"),
    (r"Generalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Generaliz"),
    (r"specialis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "specializ"),
    (r"Specialis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Specializ"),
    (r"summaris(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "summariz"),
    (r"Summaris(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Summariz"),
    (r"categoris(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "categoriz"),
    (r"Categoris(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Categoriz"),
    (r"characteris(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "characteriz"),
    (r"Characteris(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Characteriz"),
    (r"prioritis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "prioritiz"),
    (r"Prioritis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Prioritiz"),
    (r"minimis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "minimiz"),
    (r"Minimis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Minimiz"),
    (r"maximis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "maximiz"),
    (r"Maximis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Maximiz"),
    (r"normalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "normaliz"),
    (r"Normalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Normaliz"),
    (r"operationalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "operationaliz"),
    (r"Operationalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Operationaliz"),
    (r"institutionalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "institutionaliz"),
    (r"Institutionalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Institutionaliz"),
    (r"legitimis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "legitimiz"),
    (r"Legitimis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Legitimiz"),
    (r"standardis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "standardiz"),
    (r"Standardis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Standardiz"),
    (r"decentralis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "decentraliz"),
    (r"Decentralis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Decentraliz"),
    (r"centralis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "centraliz"),
    (r"Centralis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Centraliz"),
    (r"incentivis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "incentiviz"),
    (r"Incentivis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Incentiviz"),
    (r"contextualis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "contextualiz"),
    (r"Contextualis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Contextualiz"),
    (r"conceptualis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "conceptualiz"),
    (r"Conceptualis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Conceptualiz"),
    (r"rationalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "rationaliz"),
    (r"Rationalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Rationaliz"),
    (r"marginalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "marginaliz"),
    (r"Marginalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Marginaliz"),
    (r"internalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "internaliz"),
    (r"Internalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Internaliz"),
    (r"externalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "externaliz"),
    (r"Externalis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Externaliz"),
    (r"stabilis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "stabiliz"),
    (r"Stabilis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Stabiliz"),
    (r"mobilis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "mobiliz"),
    (r"Mobilis(?=e|ed|es|ing|ation|able|abilit|er\b|ers\b)", "Mobiliz"),

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
    """Every pattern matches exactly the text its replacement replaces.

    Each entry's suffix conditions are lookaheads and word boundaries, which
    match no characters, so the group that fired names the replacement
    outright. An earlier version re-ran the pattern against the matched text
    to decide — which silently stopped converting anything the moment the
    conditions became lookaheads, because a lookahead cannot be satisfied by a
    string that ends where the match ends.
    """
    def swap(match: re.Match) -> str:
        for i, (_pattern, replacement) in enumerate(PAIRS, start=1):
            if match.group(i) is not None:
                return replacement
        return match.group(0)
    return PATTERN.sub(swap, text)


def findings(text: str) -> list[str]:
    return [m.group(0) for m in PATTERN.finditer(text or "")]
