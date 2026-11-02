# Security

## Reporting something

Use GitHub's [private vulnerability
reporting](https://github.com/AO-Commons/knowledge-graph/security/advisories/new).
It reaches the maintainers without being public first.

If that is not available to you, open an issue saying only that you have
something to report and how to reach you. Do not put the details in it.

We will acknowledge within a week.

## What is worth reporting

This repository is a corpus and the tooling that maintains it. There is no
service to attack and no user data: the site is static files, and the only
credentials are GitHub Actions secrets.

What would matter:

- A way to make a workflow run code it should not, or read a secret.
- A way to get a record into the corpus without passing the scope check. The
  filing bot reads a public issue and writes to the repository, so that path
  is worth looking at hardest.
- A dependency in `pyproject.toml` with a known vulnerability that reaches
  anything running here.

What would not:

- A claim that misreads its paper, or a record that should not be here. Those
  matter a great deal and are not security — send them through
  [the correction form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=request-adjustment.yml).
- A model's output being wrong. Everything a model drafted says so, and is
  marked unreviewed until a person has checked it.

## What we can fix

The corpus quotes published papers. If you are an author and something here
misrepresents your work, that is a defect and we will fix it quickly — but
through the correction form rather than here, so the fix is public and the
history shows what changed.
