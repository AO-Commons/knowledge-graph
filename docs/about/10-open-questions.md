---
id: asked
title: Open questions
kicker: what readers ask, and which of it the field should answer
order: 10
---

Ask the library something and the question goes on a public list under your
name, beside everyone else's. The list is sorted by how many other people have
backed the same question.

This is a second source for the same object the gap statements produce, and a
weaker one. A gap statement is a published author saying in print that
something is unresolved; a question typed into a search box is somebody
wondering. The two are never mixed without saying which is which.

They are worth having for a reason the derived ones cannot supply.
`questions --propose` can only find a question the corpus already holds the
material for. A reader asking about something no held paper mentions is the
only signal this repository gets about **what is missing from it entirely** —
and with {{read}} of {{records}} records read, that is most of the field.

## What makes a question eligible

A list of everything anyone typed is a log. Five gates decide what goes on it,
in this order, and four of them cost nothing because answering already works
them out.

| Gate | Asks |
| --- | --- |
| One | Is it about autonomous organizations? |
| Two | Is it a question rather than a lookup? |
| Three | Is it still unsettled here? |
| Four | Is it a research question this field could settle? |
| Five | Has somebody already asked it? |

**Gate one** is the scope judge, the same one that decides what enters the
corpus. **Gate two** separates a question from "do you have this paper?",
which has its answer in the index rather than in the literature. **Gate
three** keeps a question out when the library already answered it well, with
citations, at strong confidence.

**Gate four** is a judge of its own, and it asks two things at once: whether
the subject is machine agents holding authority or something adjacent to it,
and whether a paper could close the question at all. A prediction, a
preference and a request for a definition cannot be closed by a paper, so none
of them is an open problem however reasonable it is. The usable form is: can
you name what a paper would have to report for the question to be closed?

**Gate five** folds a near duplicate into the question that exists rather than
starting a second one beside it. Without it the most-asked question is spread
across nine rows and the list ranks phrasings instead of questions.

A question that fails a gate is not recorded at all. That has a cost worth
knowing: a gate rejecting too much leaves no evidence that it did, and the
only way to find out is to ask the library something it should have kept.

## Gates one and four pull in opposite directions

On purpose. The scope judge that decides how to word a refusal leans towards
"in scope", because telling somebody their real question is off-topic is the
worse error when answering. The eligibility gate leans the other way, because
the list is read by people deciding what to research and one that admits
greetings is worth less than a short one. Both biases are right for their own
job and wrong for the other's.

## Seconding

One click, no cost, and it earns the person who clicks it nothing. The only
reason to press it is that you wanted the answer too, which is what makes the
count worth sorting by.

The count beside a question is how many **other** people wanted it, so you
cannot second your own. Asking something somebody has already asked seconds
theirs automatically.

## What a tag on a question means

Each one is a fact the corpus already records, in the same vocabulary the open
problems surface uses: statements that argue a position, against statements
that report a measurement.

| Tag | What it means |
| --- | --- |
| nothing on this yet | Retrieval matched no statement at all. |
| read, but not on this | The papers that would answer it are held and unread. |
| argued, not measured | Statements exist, and every one of them argues. |
| one measurement, thin | A finding bears on it, and the answer was weak anyway. |
| now an open problem | Somebody wrote the sentence and the corpus took it. |

## From a question to an open problem

Nothing is automatic. A reader-asked question is not a question node, it does
not enter `questions.yml` by itself, and the only way it becomes one is the
way everything else does: somebody reads it, writes the sentence, and opens a
pull request. The list exists to make that reading worth doing.
