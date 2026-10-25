# MIRA, vendored

The [MIRA schema](https://github.com/MIRA-science/schema) at a pinned commit,
so that validating a release against it means the same thing next month as it
does today. `PINNED` names the commit; `mira/` holds the three files the
validator needs.

```
python3 -m pip install '.[mira]'
python3 scripts/validate_mira.py data/releases/v0.10.0
```

CI runs this on every build and warns, separately, when the pin falls behind
their main — a pin nobody re-reads is a fork nobody decided on.

## Re-vendoring

```
PIN=$(git ls-remote https://github.com/MIRA-science/schema HEAD | cut -f1)
for f in mira.shacl mira.jsonld mira.ttl; do
  curl -sS -o "mira/$f" "https://raw.githubusercontent.com/MIRA-science/schema/$PIN/$f"
done
printf 'MIRA-science/schema\n%s\nfetched %s\n' "$PIN" "$(date -u +%F)" > PINNED
```

Then re-run the validator before committing. A re-vendor that is not
re-validated is worse than no re-vendor, because it looks like it was checked.

## Known quirks at this pin

**`rdfs:Resource` is a closed shape permitting no properties.** Under RDFS
inference every node in any graph is an `rdfs:Resource`, so every property on
everything becomes a violation — 2,382 of them for our release, against 0 with
inference off. `scripts/validate_mira.py` therefore runs with inference off
and offers `--infer` to reproduce the problem. It looks like a LinkML
generation default rather than a decision, their own sample data trips the
generated shapes too, and
[PR #38](https://github.com/MIRA-science/schema/pull/38) has already fixed one
case of exactly this. Worth reporting.

**Closed shapes generally.** Fifteen shapes carry `sh:closed true`, including
`Claim`, `Question` and `Evidence`, so a property of ours on one of those
nodes fails validation even in our own namespace. That is why the projection
puts nothing of ours on a MIRA node and reports the eleven fields that have
nowhere to go instead. [PR #55](https://github.com/MIRA-science/schema/pull/55)
is the open thread on this.
