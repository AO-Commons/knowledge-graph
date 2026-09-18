"""The AO Commons knowledge graph."""

CONTACT = "anke@daostar.org"
"""Who to reach about this project, sent as the User-Agent on every outbound
request.

arXiv and OpenAlex both ask for a contact address rather than rate-limiting an
anonymous client, so this is etiquette that buys throughput, not decoration.

One copy. It used to be five string literals in five modules plus two in the
site template, which is how an address outlives the job it belonged to: the
first change finds four of them and the fifth keeps writing the old one into
every request for months.
"""
