# data/overlays/

Optional layers. The graph is complete without them.

## trust

Community attachment: which AO Commons members authored or endorsed a work.
Real signal, and deliberately not part of the core graph.

**Overlay files are not committed.** `.gitignore` excludes them, because this
repository is public and the overlay names people. Keep `trust.yml` in the
private repo or locally; the public graph builds and ships without it, and no
consumer of a release can tell whether one exists.

That separation is the point twice over. It keeps a community roster out of a
public artifact, and it keeps the overlay's contribution *measurable* — build
with and without, run the same evaluation set, and compare. A signal baked
into core ranking cannot be argued with; one applied on top can be switched
off and shown to help or not.

```yaml
# data/overlays/trust.yml
weight: 1.0
authors:
  member-identifier:
    - resource:arxiv:2502.14143
endorsements:
  member-identifier:
    - resource:tool:paperclip
```

Identifiers are opaque to this package — it never reasons about who a person
is, only that some identifier relates to a work. Use a handle or a CRM record
id, never an email address.
