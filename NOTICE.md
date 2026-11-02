# Licensing

Two licenses, because this repository holds two kinds of thing.

| What | License | File |
|---|---|---|
| The taxonomy, the records, the claims, and the written documentation | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [LICENSE](LICENSE) |
| The code in `src/`, `scripts/` and `.github/` | [MIT](https://opensource.org/licenses/MIT) | [LICENSE-CODE](LICENSE-CODE) |

The split is deliberate. The corpus is the work, and asks to be credited when
it is reused. The code is a means of maintaining it, and nobody reusing a
parser should have to carry an attribution requirement into their own project.

Until November 2026 both sat in one `LICENSE` file as a summary rather than
the legal text, which GitHub reads as "Other" — so neither was machine-readable
and the data license did not show on the repository at all.

## Citing it

Use the **Cite this repository** button, or [CITATION.cff](CITATION.cff).
Releases in `data/releases/` are checksummed and keep their mistakes, so a
citation to a version means the same thing next year.

## Third-party material

Quotations from papers are held under fair dealing and carry their source.
`data/tooling/awesome-builder-tools.yml` mirrors
[framework-zero/awesome-builder-tools](https://github.com/framework-zero/awesome-builder-tools)
(MIT), pinned to the upstream commit it came from — see
[ATTRIBUTION.md](ATTRIBUTION.md).
