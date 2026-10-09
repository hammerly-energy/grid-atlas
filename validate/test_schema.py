import re
import pytest
from conftest import DATA, graphs
import build

GRAPHS = list(graphs())
IDS = [f"{g[1]}:{g[2]}" for g in GRAPHS]

@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_edges_resolve(cc, mid, arch, nodes, edges):
    bad = [e["id"] for e in edges if e["from"] not in nodes or e["to"] not in nodes]
    assert not bad, f"{mid}:{arch} dangling edges {bad}"

@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_edge_ids_unique(cc, mid, arch, nodes, edges):
    ids = [e["id"] for e in edges]
    assert len(ids) == len(set(ids))

@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_consumer_nodes_are_country_classes(cc, mid, arch, nodes, edges):
    classes = set(DATA[cc]["profile"]["consumer_classes"])
    assert {n["id"] for n in nodes.values() if n["kind"] == "consumer"} <= classes

def test_utilities_reference_real_archetypes_and_slots():
    for cc, c in DATA.items():
        for mid, m in c["markets"].items():
            slots = {n["slot"] for layer in [m["base"], *m["archetypes"].values()]
                     for n in layer.get("nodes", []) if "slot" in n}
            for name, u in m["utilities"].items():
                assert set(u["archetypes"]) <= set(m["archetypes"]), f"{mid}/{name}"
                assert set(u.get("fills", {})) <= slots, f"{mid}/{name} fills unknown slot"

def test_every_ownership_claim_has_a_source():
    """Schema enforces this too; the test makes the rule visible and covers utility fills."""
    missing = []
    for cc, mid, arch, nodes, edges in GRAPHS:
        for n in nodes.values():
            if n.get("holds_assets") and not n.get("source"):
                missing.append(f"{mid}:{n['id']} holds_assets")
            if "owner" in n and not n["owner"].get("source", {}).get("url"):
                missing.append(f"{mid}:{n['id']} owner")
    for c in DATA.values():
        for mid, m in c["markets"].items():
            for name, u in m["utilities"].items():
                for slot, f in u.get("fills", {}).items():
                    if isinstance(f, dict) and "owner" in f and not f["owner"]["source"].get("url"):
                        missing.append(f"{mid}/{name}:{slot}")
    assert not missing, missing


# ---- UI copy: abbreviations on screen are defined; glossary stays short ----
ALLOWED = {"GB", "US", "UK", "HM"}

def _tokens(s):
    return re.findall(r"[A-Za-z&]+", s)

def _is_abbr(t):
    return sum(ch.isupper() for ch in t) >= 2

def test_ui_abbreviations_are_defined():
    missing = []
    for cc, c in DATA.items():
        p = c["profile"]
        known = {t for k, v in p["glossary"].items() for t in _tokens(k + " " + v["term"])} | ALLOWED
        shown = [l["subtitle"] for l in p["lanes"].values()] + list(p["chain"])
        shown += [v for key in ("kind_labels", "component_labels", "jurisdiction_labels") for v in p[key].values()]
        shown += sorted({e["subcomponent"] for c2, _, _, _, edges in graphs() if c2 == cc for e in edges if e.get("subcomponent")})   # line item names in the bill table
        for s in shown:
            for t in _tokens(s):
                base = t[:-1] if t.endswith("s") and t[:-1].isupper() else t
                if _is_abbr(base) and base not in known:
                    missing.append(f"{cc}: {base} (in '{s}')")
    assert not missing, missing

def test_glossary_meanings_are_short():
    long = [f"{cc}:{k}" for cc, c in DATA.items() for k, v in c["profile"]["glossary"].items() if len(v["meaning"]) > 200]
    assert not long, long


# ---- domain maps: data/maps/<cc>.json, built by scripts/maps/make_maps.mjs ----
MAPS = build.load_maps()


def test_every_country_has_one_map():
    for cc in DATA:
        m = build.map_for(MAPS, cc)
        assert m["countries"][cc] in build.map_area_ids(m), f"{cc}: home area missing"


def test_map_layers_have_source_and_licence():
    for mid, m in MAPS.items():
        for l in m["layers"]:
            assert l.get("credit") and l.get("licence") and l["source"]["url"].startswith("http"), f"{mid}/{l['id']}"
            assert l["areas"], f"{mid}/{l['id']}: no shapes"


def test_map_groups_name_drawn_areas():
    for mid, m in MAPS.items():
        drawn = {a for l in m["layers"] for a in l["areas"]}
        assert drawn == set(m["bbox"]), f"{mid}: bbox out of step with areas"
        for gid, members in m.get("groups", {}).items():
            assert set(members) <= drawn, f"{mid}/{gid}: {set(members) - drawn}"


def test_maps_fit_size_budget():
    for mid in MAPS:
        size = (build.ROOT / f"data/maps/{mid}.json").stat().st_size
        assert size < 100 * 1024, f"{mid} is {size / 1024:.0f} KB"


@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_domain_area_ids_exist_in_map(cc, mid, arch, nodes, edges):
    ids = build.map_area_ids(build.map_for(MAPS, cc))
    for n in nodes.values():
        da = n.get("domain_area")
        if da:
            missing = (set(da["full"]) | set(da.get("partial", []))) - ids
            assert not missing, f"{mid}:{n['id']} names unknown areas {missing}"


def test_utility_fill_domains_exist_in_map():
    for cc, c in DATA.items():
        ids = build.map_area_ids(build.map_for(MAPS, cc))
        for mid, m in c["markets"].items():
            for name, u in m["utilities"].items():
                for slot, f in u.get("fills", {}).items():
                    da = f.get("domain_area") if isinstance(f, dict) else None
                    if da:
                        missing = (set(da["full"]) | set(da.get("partial", []))) - ids
                        assert not missing, f"{mid}/{name}:{slot} names unknown areas {missing}"


# Source-backed verification (CLAUDE.md): a line is `verified` only when two independent reviewers confirmed it
# against a primary source. Press releases, news and third-party summaries never verify a line.
SECONDARY_HOSTS = {"newsroom.cpsenergy.com"}
REVIEW = __import__("pathlib").Path(__file__).resolve().parents[1] / "docs" / "research" / "line-review.json"

def test_verified_lines_cite_a_primary_source():
    import json, urllib.parse
    verdicts = json.loads(REVIEW.read_text())["lines"] if REVIEW.exists() else {}
    bad = []
    for cc, c in DATA.items():
        for mid, m in c["markets"].items():
            for arch, layer in [("base", m["base"]), *m["archetypes"].items()]:
                for e in layer.get("edges", []):
                    if e.get("status") != "verified":
                        continue
                    key = f"{mid}/{arch}/{e['id']}"
                    v = verdicts.get(key, {})
                    if urllib.parse.urlparse(e["source"]["url"]).netloc in SECONDARY_HOSTS:
                        bad.append(f"{key}: secondary source")
                    elif [r.get("verdict") for r in v.get("reviews", [])] != ["confirm", "confirm"] or v.get("source_url") != e["source"]["url"]:
                        bad.append(f"{key}: not confirmed by both reviewers against this source")
    assert not bad, bad
