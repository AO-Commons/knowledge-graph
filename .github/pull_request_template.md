<!-- Delete whatever does not apply. A one-line PR is fine. -->

**What this changes, and why.**

---

If it touches the corpus:

- [ ] Every claim carries the exact sentence it was drawn from, and that
      sentence is in the source. `python3 scripts/check_claims.py <id>`
- [ ] Anything a model drafted says so, and is not readable as a person's
      judgment.
- [ ] Any new edge can say where it came from.

If it touches the code:

- [ ] `pytest` passes.
- [ ] No new dependency, or a reason for one that is not "it is more elegant".

If it changes a figure in the documentation, it changes the figure rather than
the sentence around it — numbers in prose go stale and nobody notices.
