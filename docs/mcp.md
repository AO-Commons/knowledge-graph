# Querying the library from Claude

The knowledge graph exposes a read-only MCP server, so Claude can search the
taxonomy, look up records and people, and read extracted claims *with the
sentence each came from*.

It runs on the reader's own machine and reads the checked-out repository. There
is no hosted endpoint yet — see [If you want people to add it by URL](#if-you-want-people-to-add-it-by-url).

## What you need first

- **Python 3.11 or newer.** `python3 --version` to check.
- **A copy of this repository.**

```bash
git clone https://github.com/AO-Commons/knowledge-graph.git
cd knowledge-graph
python3 -m pip install -e '.[mcp]'
```

If `pip` is not found, use `python3 -m pip` as above — on many macOS setups the
bare `pip` command does not exist.

Check it worked:

```bash
aokg-mcp --help 2>/dev/null || echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | aokg-mcp
```

A line of JSON naming `ao-commons-knowledge-graph` means the server is working.

## Claude Desktop

Open **Settings → Developer → Edit Config**, which opens
`claude_desktop_config.json`. On macOS it lives at
`~/Library/Application Support/Claude/claude_desktop_config.json`.

Add `ao-commons` alongside anything already there:

```json
{
  "mcpServers": {
    "ao-commons": {
      "command": "aokg-mcp"
    }
  }
}
```

Restart Claude Desktop. The server appears under the tools icon.

If Claude reports that the command cannot be found, its `PATH` does not include
the directory pip installed into. Run `which aokg-mcp` and use the full path it
prints:

```json
{
  "mcpServers": {
    "ao-commons": {
      "command": "/full/path/from/which/aokg-mcp"
    }
  }
}
```

## Claude Code

```bash
claude mcp add ao-commons -- aokg-mcp
```

Add `--scope project` to share it with everyone working in a checkout of this
repository, which writes `.mcp.json` into the repo instead of your own config.

## What to ask it

The eight tools are `coverage`, `search_topics`, `get_topic`, `search_records`,
`get_record`, `get_claims`, `get_author`, `related_records`.

Questions they answer well today:

- *What does the library hold on inter-agent trust?*
- *What has Helena Rong written, and who does she write with?*
- *What does the Melting Pot paper claim, and what sentence backs each claim?*
- *Which papers share references with this one?*
- *How much of this library has anyone actually checked?*

## What it will not tell you

**Nothing here has been reviewed yet.** Every answer says so, and that is the
point rather than a disclaimer: topic tags are a first pass, and claims are a
model's reading of a quoted sentence until a person verifies them.

So it will not answer *"what reduces cascading failures in multi-agent
systems?"* — that needs claims across the corpus, checked. Ask instead what the
library *holds* on a subject, then read the quotes.

When a claim matters, read `quoted_from_the_paper` rather than the paraphrase.
The quote is verified word-for-word against the source; the paraphrase is where
a machine could have gone wrong.

## It is read-only, deliberately

Filings and claim verdicts enter through [the review site](https://ao-commons.github.io/knowledge-graph/)
and a pull request, where a person's name is attached and the change is visible
before it lands. A tool that let an agent write into the gold set would put
unattributable judgements into the dataset every measurement is taken against.

## The corpus is read once

The server loads the corpus at start-up. After `git pull` or a rebuild, restart
Claude to pick up the change. This is deliberate — a cache that refreshed itself
could let the server disagree with the site without either of them noticing.

## If you want people to add it by URL

Everything above needs Python and a checkout, which is fine for people who work
in the repository and too much for people who only want to ask it questions.

Making it addable by URL — the way a hosted connector works — means running the
same server over HTTP somewhere public. The query layer would not change: the
server already separates the questions (`ao_commons_kg.queries`, pure functions)
from the transport, and the SDK supports an HTTP transport with no rewrite. What
it adds is hosting, and a rate limit, because the endpoint would be open.

Worth doing when the reviewed corpus is worth reading. It is not yet.
