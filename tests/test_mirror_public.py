"""The public base's seam, asserted the way the curation base's is.

This script writes to a base nobody curates, so a broken row is not caught by a
person noticing something odd. These tests hold the properties that would
otherwise fail silently: every link resolves to a row the run actually creates,
every value is something Airtable will accept, and no field name collides with
the inverse link Airtable adds on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

import mirror_public as mirror  # noqa: E402
from ao_commons_kg.facets import BY_NAME as FACETS  # noqa: E402

EXPECTED_TABLES = {"Papers", "People", "Organizations", "Tooling", "Registry"}


@pytest.fixture(scope="module")
def topics():
    return mirror.topic_labels()


@pytest.fixture(scope="module")
def tables(topics):
    return mirror.build_tables(topics)


@pytest.fixture(scope="module")
def rows(topics):
    return mirror.build_rows(topics)


def test_the_base_has_exactly_five_tables(tables):
    assert {name for name, _, _ in tables} == EXPECTED_TABLES


def test_every_table_has_a_primary_field(tables):
    for name, _, fields in tables:
        assert name in mirror.PRIMARY, f"{name} has no primary field"
        assert fields[0]["name"] == mirror.PRIMARY[name], (
            f"{name}'s first field must be its primary field — Airtable makes the "
            f"first field primary, and rows are keyed on it"
        )


def test_link_fields_name_a_table_that_exists(tables):
    names = {name for name, _, _ in tables}
    for name, _, fields in tables:
        for field in fields:
            target = field.get("_link")
            if target:
                assert target in names, f"{name}.{field['name']} links to {target!r}"


def test_no_field_collides_with_an_automatic_inverse_link(tables):
    """Airtable names each inverse after the source table.

    Defining a field of that name ourselves makes the inverse land somewhere
    unpredictable, which is the kind of breakage that only shows up in the base.
    """
    inverses = {}
    for name, _, fields in tables:
        for field in fields:
            if field.get("_link"):
                inverses.setdefault(field["_link"], set()).add(name)

    for table_name, expected in inverses.items():
        declared = {
            f["name"] for n, _, fs in tables if n == table_name for f in fs
        }
        clash = declared & expected
        assert not clash, (
            f"{table_name} declares {sorted(clash)}, which Airtable also wants for "
            f"the inverse link"
        )


def test_link_targets_all_resolve(rows, tables):
    """A dangling link shows up as a blank cell, not as an error."""
    dangling = {}
    for name, _, _ in tables:
        for key, row in rows[name].items():
            for field, targets in (row.get("_links") or {}).items():
                table = mirror.link_target(tables, name, field)
                for target in targets:
                    if target not in rows[table]:
                        dangling.setdefault(f"{name}.{field}", set()).add(target)
    assert not dangling, f"link targets with no row: {dangling}"


def test_values_are_types_airtable_accepts(rows, tables):
    for name, _, _ in tables:
        for key, row in rows[name].items():
            for field, value in row.items():
                if field == "_links":
                    continue
                assert isinstance(value, (str, int, float, bool, type(None))) or (
                    isinstance(value, list) and all(isinstance(v, str) for v in value)
                ), f"{name}.{key}.{field} is {type(value).__name__}"


def test_single_valued_facets_are_not_lists(rows):
    """A single-select handed a list is the drift that typecast would hide."""
    for key, row in rows["Papers"].items():
        for facet_name in mirror.MIRRORED_FACETS:
            label = facet_name.replace("_", " ").title()
            if label not in row:
                continue
            value = row[label]
            if FACETS[facet_name].multi:
                assert isinstance(value, list), f"{key}.{label} should be a list"
            else:
                assert isinstance(value, str), f"{key}.{label} should be one value"


def test_facet_values_are_in_the_vocabulary(rows):
    for key, row in rows["Papers"].items():
        for facet_name in mirror.MIRRORED_FACETS:
            label = facet_name.replace("_", " ").title()
            if label not in row:
                continue
            allowed = set(FACETS[facet_name].values)
            value = row[label]
            for item in (value if isinstance(value, list) else [value]):
                assert item in allowed, f"{key}.{label}: {item!r} is off-vocabulary"


def test_topic_values_are_declared_options(rows, tables, topics):
    """Every topic written to a row must be a choice the schema created."""
    declared = {
        f["name"]: {c["name"] for c in f["options"]["choices"]}
        for name, _, fields in tables for f in fields
        if f["name"] == "Topics" and name == "Papers"
    }["Topics"]
    for table in ("Papers", "Tooling"):
        for key, row in rows[table].items():
            for value in row.get("Topics", []):
                assert value in declared, f"{table}.{key}: {value!r} is not an option"


def test_topic_options_are_ordered_by_the_tree(topics):
    """2.10 comes after 2.9, which string ordering gets wrong."""
    codes = list(topics)
    if "2.9" in codes and "2.10" in codes:
        assert codes.index("2.10") > codes.index("2.9")


def test_a_tool_is_never_also_a_paper(rows):
    assert not (set(rows["Papers"]) & set(rows["Tooling"])), (
        "a record in both tables would be counted twice in every figure"
    )


def test_tooling_is_built_by_an_organization_that_has_a_row(rows):
    for key, row in rows["Tooling"].items():
        for name in row["_links"]["Built By"]:
            assert name in rows["Organizations"], (
                f"{key} is built by {name!r}, which has no Organizations row"
            )


def test_people_link_to_organizations_they_belong_to(rows):
    linked = [k for k, v in rows["People"].items()
              if v.get("_links", {}).get("Organizations")]
    assert linked, "no person is linked to an organization; affiliations were lost"
    for name in linked:
        for org in rows["People"][name]["_links"]["Organizations"]:
            assert org in rows["Organizations"]


def test_registry_rows_carry_a_stable_id(rows):
    for key, row in rows["Registry"].items():
        assert row["ID"] == key and key, "a registry row must be keyed by its slug"


# --- the guard, the retries, and the unreadable source -------------------


def _push(monkeypatch, live, wanted):
    """Run push_table against a fake base, returning what it tried to write."""
    calls = []
    monkeypatch.setattr(mirror, "fetch_all", lambda *a, **k: live)
    monkeypatch.setattr(
        mirror, "api", lambda method, url, token, **kw: calls.append((method, kw)) or {}
    )
    mirror.push_table("appX", "tblX", "T", wanted, "ID", "tok", dry=False)
    return calls


def deleted(calls):
    return [c for c in calls if c[0] == "DELETE"]


def test_guard_protects_a_table_too_small_to_hit_a_percentage(monkeypatch):
    """Four hand-made rows is exactly the table nobody notices losing."""
    live = [{"id": f"rec{i}", "fields": {"ID": f"old{i}"}} for i in range(4)]
    calls = _push(monkeypatch, live, {"new": {"ID": "new"}})
    assert not deleted(calls), "all four rows would have been retired"


def test_guard_allows_retiring_a_single_row(monkeypatch):
    live = [{"id": f"rec{i}", "fields": {"ID": f"k{i}"}} for i in range(8)]
    wanted = {f"k{i}": {"ID": f"k{i}"} for i in range(8) if i != 3}
    assert deleted(_push(monkeypatch, live, wanted)), "one stale row should retire"


def test_guard_refuses_to_clear_a_table_the_source_says_is_empty(monkeypatch):
    live = [{"id": "rec1", "fields": {"ID": "only"}}]
    assert not deleted(_push(monkeypatch, live, {}))


def test_an_unreadable_source_skips_the_table_rather_than_clearing_it(monkeypatch):
    calls = []
    monkeypatch.setattr(mirror, "fetch_all", lambda *a, **k: calls.append("read") or [])
    monkeypatch.setattr(mirror, "api", lambda *a, **k: calls.append("write") or {})
    assert mirror.push_table("appX", "tblX", "Registry", None, "ID", "t", dry=False) == {}
    assert not calls, "a skipped table must not be read or written"


def test_registry_unavailable_becomes_none_not_empty(monkeypatch):
    """None means 'leave it alone'; {} would mean 'the registry was emptied'."""
    monkeypatch.setattr(mirror, "REGISTRY_LOCAL", Path("/nonexistent/registry.json"))
    monkeypatch.setattr(
        mirror.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no network")),
    )
    assert mirror.build_rows(mirror.topic_labels())["Registry"] is None


def test_api_retries_a_rate_limit_then_succeeds(monkeypatch):
    attempts = []

    class Response:
        def __init__(self, code):
            self.status_code, self.ok, self.headers = code, code == 200, {}
            self.text = ""

        def json(self):
            return {"ok": True}

    def request(method, url, **kwargs):
        attempts.append(method)
        return Response(429 if len(attempts) < 3 else 200)

    monkeypatch.setattr(mirror.requests, "request", request)
    monkeypatch.setattr(mirror.time, "sleep", lambda s: None)
    assert mirror.api("GET", "http://x", "tok") == {"ok": True}
    assert len(attempts) == 3


def test_api_does_not_retry_a_permission_error(monkeypatch):
    attempts = []

    class Response:
        status_code, ok, headers, text = 403, False, {}, "forbidden"

        def json(self):
            return {}

    def request(method, url, **kwargs):
        attempts.append(method)
        return Response()

    monkeypatch.setattr(mirror.requests, "request", request)
    monkeypatch.setattr(mirror.time, "sleep", lambda s: None)
    with pytest.raises(mirror.requests.HTTPError):
        mirror.api("GET", "http://x", "tok")
    assert len(attempts) == 1, "a 403 is a fact, not a phase — retrying wastes the run"
