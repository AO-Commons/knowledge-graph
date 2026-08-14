# evals/gold/

Human-assigned taxonomy topics. The thing every classification number is
measured against.

```sh
aokg review --reviewer your-name
```

Walks records one at a time, showing title, abstract, current tags, and about
a dozen suggested topics with their place in the tree. Type the numbers that
apply. `/text` searches all 568 topics when nothing suggested fits, `c 2.2,9.1`
enters codes directly, `n` records that none apply, `s` skips, `q` saves and
quits.

Resumable — anything already recorded is skipped, so this works in several
sittings. It saves every five records as well as on exit.

Then:

```sh
aokg evaluate
```

## Why this exists

Every accuracy figure reported so far is measured against my own first-pass
tags, which are themselves `unreviewed`. That measures *similarity to those
tags*, not accuracy — if both the classifier and the tags are wrong in the
same way, the number looks fine.

Roughly 30 reviewed records make the figures indicative; 50 make them worth
tuning against. Below 30 `evaluate` says so rather than printing a number
that will get quoted.

## Two decisions the tool makes for you

**The sample is stratified across taxonomy sections**, not taken in order. A
gold set drawn from whatever came first would measure one corner of the
corpus and report it as the whole. Records with abstracts are offered first
within each section, because a record cannot be fairly judged from its title
— and neither can the classifier.

**"None of these apply" is a real answer**, recorded rather than skipped. It
says the record is out of scope, or that the taxonomy has a gap worth a
proposal. Skipping throws that judgement away.

## What not to do

Don't review only the records you find interesting, and don't review only the
ones the classifier gets wrong. Both produce a number that cannot be compared
to anything.
