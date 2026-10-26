---
id: next
title: Roadmap
order: 14
---

**Now. Get the statements reviewed.**

- {{read}} papers and {{statements}} statements are open on the review screen;
  {{reviewed}} have been judged.
- Nothing here has an accuracy number until more of this is done, because it
  is what every other figure would be measured against.
- Review is the one thing in the pipeline no machine does, and it is the
  binding constraint on everything below.

**Next. Reach the papers we cannot read.**

- Only arXiv has a full-text path today, so most of {{records}} records have no
  route to their own body.
- Building the Loop took a browser to reach and turned out to be fifty-five
  times the length of its abstract.
- Every record should say what anyone was able to read, so the shape of the
  problem is visible rather than found one paper at a time.

**Then. Extraction across the corpus.**

- Run the gated process over the rest, tiered by what a paper is: argument
  papers repay a deep read, benchmark papers mostly yield instrument detail
  the gates refuse.
- Publish an extraction accuracy figure against the reviewed set.

**After that. Linking, and what makes review worth doing.**

- Bring relation tags back to the review screen once there are enough
  statements for the pairs to be worth meeting mid-task.
- Citations as a second proposal signal: if A cites B, A's statements are
  candidates for relations to B's.
- Propose question clusters rather than reading for them by hand. The concepts
  are already there, and `--propose` is the first half of it.
- Mark a question answered when something has been shown on it. Nothing does
  this today and `status` is set by hand.
- The organization layer. Affiliations are resolved for a fraction of records,
  and reputation is what would make review worth doing.
- Earning is half built. Judging an answer and having a question backed both
  return credit; reviewing a statement and finishing a paper are declared in
  the ledger and award nothing yet, and reviewing is the scarce good.
- A maintainer's reply should come back to the person who filed. Closing an
  issue does; a comment on it does not, and the question page would have to
  become a thread for it to.
- Promote a reader-asked question into the corpus. The list makes the reading
  worth doing and nothing carries the result back into `questions.yml`.
- **The ecosystem map.** Organizations and people are nodes and the edges run
  between them, but affiliation data reaches only a minority of records, and
  almost nobody has an identity link. The map will look sparser than the
  corpus is until both improve.
- **What MIRA cannot carry.** Six things, counted in every release's
  `mira-report.json` and written up for the people who maintain it: a class
  for an organization, an edge from a paper to the claim it asserts, whose
  result a statement is, who checked it, two relations from CiTO, and a home
  for a tool or a deployment.

**Later. v1.**

- A citable release with a measured accuracy figure.
- A browser extension, so adding from an arXiv or DOI page is one click.
